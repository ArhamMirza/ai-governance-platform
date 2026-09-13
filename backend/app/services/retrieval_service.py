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
    # What this passage is: an uploaded file, a policy, an inventory row.
    source_type: str
    source_id: int
    source_title: str
    # What it is about -- for a document, the record it was filed against.
    entity_type: str
    entity_id: int
    section: str | None
    source: str
    text: str
    score: float
    injection_findings: list[str] = field(default_factory=list)

    @property
    def reference(self) -> str:
        """How this passage is named to the model and in the UI."""
        where = f", {self.section}" if self.section else ""
        scanned = " (read by OCR)" if self.source == "ocr" else ""
        return f"{self.source_title}{where}{scanned}"


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


def _scope_evidence(statement, entity_type: str | None, entity_id: int | None):  # noqa: ANN001
    if entity_type is not None:
        statement = statement.where(Evidence.entity_type == entity_type)
    if entity_id is not None:
        statement = statement.where(Evidence.entity_id == entity_id)
    return statement


def _in_scope(chunk: DocumentChunk, entity_type: str | None, entity_id: int | None) -> bool:
    """Whether a passage belongs to what the caller asked about.

    Read off the chunk itself. The model supplies a query string and never a
    query; which records it may see is decided here, on our side.
    """
    if entity_type is not None and chunk.entity_type != entity_type:
        return False
    return not (entity_id is not None and chunk.entity_id != entity_id)


def coverage_gaps(
    db: Session, entity_type: str | None = None, entity_id: int | None = None
) -> list[CoverageGap]:
    """Documents in scope that are not searchable, and why."""
    statement = _scope_evidence(
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
    # Bring the index up to date before reading it. Records are queued for
    # reindexing when they change and the work is done here, at the one
    # moment staleness would actually be visible -- so a risk score edited a
    # second ago is not answered from its old value. Bounded, so a bulk
    # import cannot turn one search into a minutes-long wait; whatever is
    # left is picked up by the next search or the backfill command.
    from app.services import document_index_service

    document_index_service.drain(db)

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

    chunks = document_index_repository.chunks_by_id(db, [chunk_id for chunk_id, _ in ranked])

    citations: list[Citation] = []
    for chunk_id, score in ranked:
        chunk: DocumentChunk | None = chunks.get(chunk_id)
        if chunk is None or not _in_scope(chunk, entity_type, entity_id):
            continue
        citations.append(
            Citation(
                chunk_id=chunk.id,
                source_type=str(chunk.source_type),
                source_id=chunk.source_id,
                source_title=chunk.source_title,
                entity_type=str(chunk.entity_type),
                entity_id=chunk.entity_id,
                section=chunk.section,
                source=str(chunk.source),
                text=chunk.text,
                score=score,
                injection_findings=list(chunk.injection_findings or []),
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
