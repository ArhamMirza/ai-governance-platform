"""Finding the passages that actually answer a question.

Two retrievers run over the same corpus and their rankings are fused.
Keyword search catches what vectors are worst at -- a control id like
"A.5.23", a product name, an exact date -- and vector search catches what
keywords are worst at, which is a question phrased nothing like the document
that answers it. Fusing them is not belt-and-braces; each covers the other's
characteristic failure.

A third step runs after fusion: the fused top RERANK_CANDIDATES are handed
to a local cross-encoder (see reranking.py) that reads the query and each
passage together, rather than comparing them independently the way BM25 and
the bi-encoder embedding both do. That catches passages which merely share
vocabulary with the query but don't actually answer it -- the fused order
alone can't tell those apart.

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

from app.core import embeddings, reranking
from app.models.document_chunk import DocumentChunk, IndexStatus
from app.models.evidence import Evidence
from app.repositories import document_index_repository

DEFAULT_LIMIT = 6

# How many of the fused, in-scope candidates get reranked. Every caller's
# limit is well under this (DEFAULT_LIMIT is 6; the widest is 16 sources
# spread across many queries, never 16 from one), so nothing past this
# window could ever be returned anyway -- reranking more would just cost
# more cross-encoder calls for candidates that can't surface.
RERANK_CANDIDATES = 20

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

    if not _HAS_WORD_CHARACTER.search(query):
        return SearchResult(citations=[], mode="keyword", coverage_gaps=gaps)

    citations, mode = _ranked_citations(
        db, query, embeddings.embed_query(query), entity_type=entity_type, entity_id=entity_id,
        limit=limit,
    )
    return SearchResult(citations=citations, mode=mode, coverage_gaps=gaps)


def search_with_vector(
    db: Session,
    query: str,
    query_vector: list[float] | None,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = DEFAULT_LIMIT,
) -> SearchResult:
    """Hybrid search using an already-computed query embedding.

    For a caller that runs the *same* query text against several different
    scopes back to back -- whole-assessment drafting does this once per
    section, scoped first to the AI system, then the assessment, then the
    organisation at large -- embedding is the expensive step (real ONNX
    inference, unlike the cheap SQL either side of it), and the vector for a
    given piece of text does not depend on which scope it is then searched
    against. Calling ``search()`` three times for that recomputed it three
    times for an identical result. This takes the vector once, from
    ``embeddings.embed_query``, and reuses it.

    Deliberately skips the index drain and the coverage-gap query that
    ``search()`` does: both are real DB round trips a caller making several
    of these calls in a row does not want paid three times over for the same
    outcome. Call ``document_index_service.drain`` once yourself first, and
    ``coverage_gaps`` once for whatever scope you actually need it in --
    exactly what the drafting caller this was built for already did.
    """
    if not _HAS_WORD_CHARACTER.search(query):
        return SearchResult(citations=[], mode="keyword")
    citations, mode = _ranked_citations(
        db, query, query_vector, entity_type=entity_type, entity_id=entity_id, limit=limit,
    )
    return SearchResult(citations=citations, mode=mode)


def _ranked_citations(
    db: Session,
    query: str,
    query_vector: list[float] | None,
    *,
    entity_type: str | None,
    entity_id: int | None,
    limit: int,
) -> tuple[list[Citation], str]:
    keyword_ids = document_index_repository.keyword_ranked(db, query)
    vector_hits = document_index_repository.vector_ranked(db, query_vector)
    mode = "hybrid" if vector_hits else "keyword"

    # The floor, applied before fusion so an unrelated passage cannot be
    # carried in by its rank in one list alone.
    near_enough = {
        chunk_id for chunk_id, distance in vector_hits if distance <= MAX_VECTOR_DISTANCE
    }
    admissible = set(keyword_ids) | near_enough
    if not admissible:
        return [], mode

    ranked = document_index_repository.fuse(
        [i for i in keyword_ids if i in admissible],
        [chunk_id for chunk_id, _ in vector_hits if chunk_id in admissible],
    )

    chunks = document_index_repository.chunks_by_id(db, [chunk_id for chunk_id, _ in ranked])

    candidates: list[tuple[DocumentChunk, float]] = []
    for chunk_id, score in ranked:
        chunk: DocumentChunk | None = chunks.get(chunk_id)
        if chunk is None or not _in_scope(chunk, entity_type, entity_id):
            continue
        candidates.append((chunk, score))
        if len(candidates) >= RERANK_CANDIDATES:
            break

    candidates = _reranked(query, candidates)

    citations = [
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
        for chunk, score in candidates[:limit]
    ]

    return citations, mode


def _reranked(
    query: str, candidates: list[tuple[DocumentChunk, float]]
) -> list[tuple[DocumentChunk, float]]:
    """Candidates in cross-encoder order, each still paired with its fusion
    score. Unchanged if the reranker can't run here -- fusion order is a
    reasonable ranking on its own, and search should degrade, not break."""
    if not candidates:
        return candidates
    cross_scores = reranking.rerank(query, [chunk.text for chunk, _ in candidates])
    if cross_scores is None:
        return candidates
    return [
        pair
        for _, pair in sorted(
            zip(cross_scores, candidates, strict=True), key=lambda paired: paired[0], reverse=True
        )
    ]


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
