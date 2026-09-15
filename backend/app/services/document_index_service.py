"""Making the record searchable: extract or render, scan, chunk, embed.

Two kinds of source go through the same pipeline and end up in the same
index. An uploaded file has to be read -- parsed, OCR'd, decoded -- and can
fail at it, which is why evidence carries an index status saying whether the
assistant can see it. A governance record is already structured, so there is
nothing to fail at; it is rendered to labelled text and indexed.

Everything here is written so a failure leaves a record of what happened
rather than an exception that loses the source. Indexing is a convenience
layered on top of the data, and the data must never be harmed by it.

The scan step deserves its name. Uploaded documents are the highest-risk
input in this system -- a person can be told not to paste instructions at a
model, a PDF cannot -- so every chunk is checked for text that reads as an
instruction, and what is found is recorded on the chunk and, for evidence,
on the evidence row. It is never removed: a governance platform legitimately
holds documents *about* prompt injection, and editing a compliance record to
make a scanner happy would be a far worse bug than the one it prevents.
"""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core import ai_prompting, embeddings
from app.core.chunking import Chunk, chunk_segments
from app.models.document_chunk import DocumentChunk, IndexStatus, SourceType
from app.models.evidence import Evidence
from app.models.index_queue import IndexQueueEntry
from app.repositories import document_index_repository
from app.services import document_extraction, record_rendering

# Findings are for a person to read, so the list stays short enough to read.
MAX_RECORDED_FINDINGS = 10
# How much of the queue one search is willing to work through before
# answering. Bounded so a bulk import cannot turn the next search into a
# minutes-long wait; the remainder is picked up by the next drain or the
# backfill command.
DRAIN_BUDGET = 25


def _mark(
    evidence: Evidence, status: IndexStatus, detail: str | None, findings: list[str] | None = None
) -> None:
    evidence.index_status = status
    evidence.index_detail = detail
    evidence.indexed_at = datetime.now(UTC)
    evidence.injection_findings = findings or None


def _scan(chunks: list[Chunk]) -> list[list[str]]:
    return [ai_prompting.scan_for_injection(chunk.text) for chunk in chunks]


def _store(
    db: Session,
    chunks: list[Chunk],
    findings: list[list[str]],
    *,
    source_type: str,
    source_id: int,
    source_title: str,
    entity_type: str,
    entity_id: int,
) -> list[DocumentChunk]:
    rows = [
        DocumentChunk(
            source_type=source_type,
            source_id=source_id,
            source_title=source_title,
            entity_type=entity_type,
            entity_id=entity_id,
            ordinal=chunk.ordinal,
            text=chunk.text,
            section=chunk.section,
            source=chunk.source,
            token_estimate=chunk.token_estimate,
            injection_findings=found or None,
        )
        for chunk, found in zip(chunks, findings, strict=False)
    ]
    vectors = embeddings.embed_passages([chunk.text for chunk in chunks])
    return document_index_repository.add_chunks(db, rows, vectors or None)


# ---------- uploaded documents ----------


def index_evidence(db: Session, evidence_id: int) -> Evidence | None:
    """Index one uploaded document. Returns the row, or None if it's gone."""
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        return None

    document_index_repository.clear_for_source(db, SourceType.EVIDENCE, evidence_id)

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

    findings = _scan(chunks)
    rows = _store(
        db,
        chunks,
        findings,
        source_type=SourceType.EVIDENCE,
        source_id=evidence_id,
        source_title=evidence.filename,
        entity_type=evidence.entity_type,
        entity_id=evidence.entity_id,
    )

    detail = extraction.detail or f"{len(rows)} passage(s) indexed."
    if not embeddings.available():
        # Said plainly rather than hidden: keyword-only search is materially
        # worse at questions phrased differently from the document.
        detail += " Indexed for keyword search only (no embedding model available)."

    document_findings = sorted({f for found in findings for f in found})
    _mark(evidence, IndexStatus.INDEXED, detail, document_findings[:MAX_RECORDED_FINDINGS])
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


# ---------- governance records ----------


def index_record(db: Session, source_type: str, source_id: int) -> int:
    """Index one governance record. Returns how many passages it produced.

    A record that has been deleted, or that renders to nothing, leaves the
    index with nothing for it -- which is the correct outcome either way,
    since a search must not return a record that is gone.
    """
    document_index_repository.clear_for_source(db, source_type, source_id)

    rendered = record_rendering.render(db, source_type, source_id)
    if rendered is None:
        return 0

    chunks = chunk_segments(rendered.segments)
    if not chunks:
        return 0

    rows = _store(
        db,
        chunks,
        _scan(chunks),
        source_type=source_type,
        source_id=source_id,
        source_title=rendered.title,
        entity_type=rendered.entity_type,
        entity_id=rendered.entity_id,
    )
    return len(rows)


# ---------- the queue ----------


def mark_stale(db: Session, source_type: str, source_id: int) -> None:
    """Note that a source's text has changed and its index is out of date.

    Written in the caller's transaction, so a committed change and its
    pending reindex are never out of step.
    """
    existing = db.scalar(
        select(IndexQueueEntry).where(
            IndexQueueEntry.source_type == source_type,
            IndexQueueEntry.source_id == source_id,
        )
    )
    if existing is None:
        db.add(IndexQueueEntry(source_type=source_type, source_id=source_id))


def drain(db: Session, limit: int | None = DRAIN_BUDGET) -> dict[str, int]:
    """Reindex queued sources. Returns how many of each kind were done.

    Each entry is handled independently: one record that cannot be indexed
    is dropped from the queue with the rest of the run carrying on, rather
    than blocking every other record behind it forever.
    """
    statement = select(IndexQueueEntry).order_by(IndexQueueEntry.id)
    if limit is not None:
        statement = statement.limit(limit)
    entries = list(db.scalars(statement))

    tally: dict[str, int] = {}
    for entry in entries:
        source_type, source_id = entry.source_type, entry.source_id
        try:
            index_record(db, source_type, source_id)
        except Exception:  # noqa: BLE001 -- one bad record must not stall the queue
            db.rollback()
        db.execute(delete(IndexQueueEntry).where(IndexQueueEntry.id == entry.id))
        db.commit()
        tally[source_type] = tally.get(source_type, 0) + 1
    return tally


def queue_depth(db: Session) -> int:
    return db.query(IndexQueueEntry).count()


# ---------- backfill ----------


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
    """Index every document still pending. Returns a count per outcome."""
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
