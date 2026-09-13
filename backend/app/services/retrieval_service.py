"""Finding the passages that actually answer a question.

Two retrievers run over the same corpus and their rankings are fused.
Keyword search catches what vectors are worst at -- a control id like
"A.5.23", a product name, an exact date -- and vector search catches what
keywords are worst at, which is a question phrased nothing like the document
that answers it. Fusing them is not belt-and-braces; each covers the other's
characteristic failure.

Two things here matter more than ranking:

**Returning nothing is a valid answer.** Something is always nearest in
vector space, so "the closest passage" is not evidence of anything. A result
has to clear a floor -- it literally contains the words, or it is genuinely
close -- and when nothing does, this returns nothing so the assistant can
say the record does not cover it.

**What could not be searched is reported.** A document that failed to index
is invisible to search but present in the record, and an assistant that
cannot tell "nothing found" from "could not look" will state the first while
the second is true. Every search carries its coverage gaps back with it.
"""

import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import embeddings
from app.models.document_chunk import DocumentChunk, IndexStatus
from app.models.evidence import Evidence
from app.repositories import document_index_repository

DEFAULT_LIMIT = 6

# L2 distance between normalised bge-small-en-v1.5 embeddings, above which a
# passage is treated as unrelated however well it ranked.
#
# Calibrated by measurement, not taste. BGE has a high similarity floor --
# two unrelated English sentences still score around cosine 0.4-0.5 -- so the
# usable signal sits in a narrow band. On a sample corpus of governance
# policies, a question genuinely answered by a passage measured L2 0.75
# (cosine 0.72), while every unrelated pairing measured 0.99 to 1.12. 0.9
# sits in that gap. An earlier, "generous" 1.2 admitted literally everything
# and made the refusal path dead code.
#
# It is model-specific: changing the embedding model means re-measuring this.
MAX_VECTOR_DISTANCE = 0.9

# Unicode-aware on purpose: this rejects punctuation-only queries without
# also rejecting scripts that the ASCII keyword tokeniser cannot index. Such
# a query reaches vector search alone, which is a real limitation of the
# keyword half rather than something to pretend away here.
_HAS_WORD_CHARACTER = re.compile(r"\w", re.UNICODE)


@dataclass
class Citation:
    """One retrieved passage, and everything needed to check it."""

    chunk_id: int
    evidence_id: int
    filename: str
    section: str | None
    source: str
    entity_type: str
    entity_id: int
    text: str
    score: float
    injection_findings: list[str] = field(default_factory=list)

    @property
    def reference(self) -> str:
        """How this passage is named to the model and in the UI."""
        where = f", {self.section}" if self.section else ""
        scanned = " (read by OCR)" if self.source == "ocr" else ""
        return f"{self.filename}{where}{scanned}"


@dataclass
class CoverageGap:
    """A document in scope that search could not see into."""

    evidence_id: int
    filename: str
    status: str
    detail: str | None


@dataclass
class SearchResult:
    citations: list[Citation]
    # "hybrid" when both retrievers ran, "keyword" when this deployment has
    # no embedding model or no sqlite-vec. Surfaced so a thin answer can be
    # explained rather than just being thin.
    mode: str
    coverage_gaps: list[CoverageGap] = field(default_factory=list)

    @property
    def chunk_ids(self) -> set[int]:
        return {c.chunk_id for c in self.citations}


def _scope(statement, entity_type: str | None, entity_id: int | None):  # noqa: ANN001
    if entity_type is not None:
        statement = statement.where(Evidence.entity_type == entity_type)
    if entity_id is not None:
        statement = statement.where(Evidence.entity_id == entity_id)
    return statement


def coverage_gaps(
    db: Session, entity_type: str | None = None, entity_id: int | None = None
) -> list[CoverageGap]:
    """Documents in scope that are not searchable, and why."""
    statement = _scope(
        select(Evidence).where(Evidence.index_status != IndexStatus.INDEXED),
        entity_type,
        entity_id,
    ).order_by(Evidence.id)
    return [
        CoverageGap(
            evidence_id=row.id,
            filename=row.filename,
            status=str(row.index_status),
            detail=row.index_detail,
        )
        for row in db.scalars(statement)
    ]


def search(
    db: Session,
    query: str,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = DEFAULT_LIMIT,
) -> SearchResult:
    """The passages that best answer ``query``, or none if none do."""
    gaps = coverage_gaps(db, entity_type, entity_id)

    # A query with no word characters at all is punctuation, and there is
    # nothing to ground an answer in. Worth its own guard rather than letting
    # it through: an empty query embeds to a zero vector, which sits within
    # the distance floor of every passage in the corpus and would return the
    # whole record as "relevant".
    if not _HAS_WORD_CHARACTER.search(query):
        return SearchResult(citations=[], mode="keyword", coverage_gaps=gaps)

    keyword_ids = document_index_repository.keyword_ranked(db, query)
    vector_hits = document_index_repository.vector_ranked(db, embeddings.embed_query(query))
    mode = "hybrid" if vector_hits else "keyword"

    # The floor, applied before fusion so an unrelated passage cannot be
    # carried in by its rank in one list alone.
    near_enough = {
        chunk_id for chunk_id, distance in vector_hits if distance <= MAX_VECTOR_DISTANCE
    }
    admissible = set(keyword_ids) | near_enough
    if not admissible:
        return SearchResult(citations=[], mode=mode, coverage_gaps=gaps)

    ranked = document_index_repository.fuse(
        [i for i in keyword_ids if i in admissible],
        [chunk_id for chunk_id, _ in vector_hits if chunk_id in admissible],
    )

    # Scoping is applied here, on our side, against what the caller asked
    # for -- the model supplies a query string and never a query.
    chunks = document_index_repository.chunks_by_id(db, [chunk_id for chunk_id, _ in ranked])
    evidence_rows = {
        row.id: row
        for row in db.scalars(
            _scope(
                select(Evidence).where(
                    Evidence.id.in_({c.evidence_id for c in chunks.values()} or {0})
                ),
                entity_type,
                entity_id,
            )
        )
    }

    citations: list[Citation] = []
    for chunk_id, score in ranked:
        chunk: DocumentChunk | None = chunks.get(chunk_id)
        if chunk is None:
            continue
        evidence = evidence_rows.get(chunk.evidence_id)
        if evidence is None:
            continue  # out of scope for this search
        citations.append(
            Citation(
                chunk_id=chunk.id,
                evidence_id=evidence.id,
                filename=evidence.filename,
                section=chunk.section,
                source=str(chunk.source),
                entity_type=evidence.entity_type,
                entity_id=evidence.entity_id,
                text=chunk.text,
                score=score,
                injection_findings=list(evidence.injection_findings or []),
            )
        )
        if len(citations) >= limit:
            break

    return SearchResult(citations=citations, mode=mode, coverage_gaps=gaps)


def verify_cited_ids(cited: list[int], retrieved: set[int]) -> tuple[list[int], list[int]]:
    """Split cited chunk ids into those that were retrieved and those invented.

    Deterministic, free, and it catches the failure a reader is least able
    to catch themselves: a confident answer citing a source that was never
    in front of the model. No judgement about whether the passage supports
    the claim -- only whether the model was ever shown it.
    """
    supported = [chunk_id for chunk_id in cited if chunk_id in retrieved]
    fabricated = [chunk_id for chunk_id in cited if chunk_id not in retrieved]
    return supported, fabricated
