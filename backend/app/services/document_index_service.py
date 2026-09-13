"""Making an uploaded document searchable: extract, scan, chunk, embed.

Runs once per file, and again on demand. The whole pipeline is written so
that a failure anywhere leaves a record of what happened rather than an
exception that loses the file: indexing is a convenience layered on top of
evidence, and evidence is the thing that must never be harmed by it.

The scan step deserves its name. Uploaded documents are the highest-risk
input in this system -- a person can be told not to paste instructions at a
model, a PDF cannot -- so every chunk is checked for text that reads as an
instruction, and what is found is recorded on the evidence row. It is never
removed: a governance platform legitimately holds documents *about* prompt
injection, and editing a compliance record to make a scanner happy would be
a far worse bug than the one it prevents.
"""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ai_prompting, embeddings
from app.core.chunking import chunk_segments
from app.models.document_chunk import DocumentChunk, IndexStatus
from app.models.evidence import Evidence
from app.repositories import document_index_repository
from app.services import document_extraction

# Findings are for a person to read, so the list stays short enough to read.
MAX_RECORDED_FINDINGS = 10


def _mark(
    evidence: Evidence, status: IndexStatus, detail: str | None, findings: list[str] | None = None
) -> None:
    evidence.index_status = status
    evidence.index_detail = detail
    evidence.indexed_at = datetime.now(UTC)
    evidence.injection_findings = findings or None


def index_evidence(db: Session, evidence_id: int) -> Evidence | None:
    """Index one document. Returns the evidence row, or None if it's gone."""
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        return None

    document_index_repository.clear_for_evidence(db, evidence_id)

    try:
        data = Path(evidence.storage_path).read_bytes()
    except OSError as exc:
        _mark(
            evidence,
            IndexStatus.UNREADABLE,
            f"The stored file could not be read ({exc.strerror}).",
        )
        db.commit()
        return evidence

    extraction = document_extraction.extract(evidence.filename, data)
    if extraction.status is not IndexStatus.INDEXED:
        _mark(evidence, extraction.status, extraction.detail)
        db.commit()
        return evidence

    chunks = chunk_segments(extraction.segments)
    if not chunks:
        _mark(evidence, IndexStatus.EMPTY, "No passages could be formed from this file.")
        db.commit()
        return evidence

    findings: list[str] = []
    for chunk in chunks:
        for finding in ai_prompting.scan_for_injection(chunk.text):
            if finding not in findings:
                findings.append(finding)

    vectors = embeddings.embed_passages([chunk.text for chunk in chunks])
    rows = [
        DocumentChunk(
            evidence_id=evidence_id,
            ordinal=chunk.ordinal,
            text=chunk.text,
            section=chunk.section,
            source=chunk.source,
            token_estimate=chunk.token_estimate,
        )
        for chunk in chunks
    ]
    document_index_repository.add_chunks(db, rows, vectors or None)

    detail = extraction.detail or f"{len(rows)} passage(s) indexed."
    if not vectors:
        # Said plainly rather than hidden: keyword-only search is materially
        # worse at questions phrased differently from the document.
        detail += " Indexed for keyword search only (no embedding model available)."
    _mark(evidence, IndexStatus.INDEXED, detail, findings[:MAX_RECORDED_FINDINGS])
    db.commit()
    return evidence


def index_quietly(db: Session, evidence_id: int) -> None:
    """Index without ever letting a failure reach the caller.

    Used on the upload path, where the document is already safely stored and
    recorded. A file that cannot be indexed is a search gap, reported as
    one; it is not a reason to fail the upload the person just made.
    """
    try:
        index_evidence(db, evidence_id)
    except Exception as exc:  # noqa: BLE001 -- indexing must never break an upload
        try:
            db.rollback()
            evidence = db.get(Evidence, evidence_id)
            if evidence is not None:
                _mark(
                    evidence,
                    IndexStatus.UNREADABLE,
                    f"Indexing failed ({type(exc).__name__}). The file itself is stored and safe.",
                )
                db.commit()
        except Exception:  # noqa: BLE001
            # Recording why indexing failed must not itself be able to fail --
            # if the database is the thing that is broken, the write above is
            # the next thing to raise, and this runs in a background task
            # whose exception surfaces nowhere useful.
            db.rollback()


def pending_evidence_ids(db: Session) -> list[int]:
    """Documents uploaded before search existed, or awaiting a retry."""
    return list(
        db.scalars(
            select(Evidence.id)
            .where(Evidence.index_status == IndexStatus.PENDING)
            .order_by(Evidence.id)
        )
    )


def backfill(db: Session, limit: int | None = None) -> dict[str, int]:
    """Index everything still pending. Returns a count per outcome."""
    ids = pending_evidence_ids(db)
    if limit is not None:
        ids = ids[:limit]

    tally: dict[str, int] = {}
    for evidence_id in ids:
        index_quietly(db, evidence_id)
        evidence = db.get(Evidence, evidence_id)
        status = str(evidence.index_status) if evidence else "missing"
        tally[status] = tally.get(status, 0) + 1
    return tally
