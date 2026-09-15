"""The three tables document search runs on, written in one place.

A chunk lives in ``document_chunks``, its text in an FTS5 mirror and its
embedding in a sqlite-vec table, all keyed on the chunk's id. Nothing else in
the app writes to the latter two: if a chunk could be inserted in one place
and not another, search would quietly return passages whose text no longer
matches the record, which is the kind of wrong that looks right.

Vector search is optional. Where sqlite-vec cannot be loaded, writes skip the
vector table and search runs on keywords alone -- see
``app.core.vector_store``.
"""

import re

from sqlalchemy import delete, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.vector_store import EMBEDDING_DIMENSIONS, serialize, vectors_available
from app.models.document_chunk import DocumentChunk

# How deep each retriever goes before the two lists are fused. Wide enough
# that a passage ranked poorly by one method can still be rescued by the
# other, which is the whole point of running both.
CANDIDATES_PER_METHOD = 100
# Reciprocal Rank Fusion's damping constant. 60 is the value from the
# original TREC work and the one the sqlite-vec hybrid-search literature
# uses; it keeps any single list from dominating on rank alone.
RRF_K = 60

# A term is a run of word characters that may contain internal dots or
# hyphens, so "A.5.23" and "ISO-42001" survive whole. Matching plain words
# instead shatters a control id into the fragments "5" and "23", and a search
# for A.5.23 then matches any document mentioning 23 -- losing precisely the
# case keyword search is carried for.
_TERM = re.compile(r"[A-Za-z0-9_]+(?:[.\-][A-Za-z0-9_]+)*")

# Dropped from keyword queries. These carry almost no signal and a great deal
# of noise: OR-joined, a single "before" out of a user's sentence matches any
# document containing the word and then earns a fusion score for doing so.
# Measured on a real corpus, this was the difference between the right
# document ranking first and a vendor policy ranking first because it
# happened to contain "before".
_STOPWORDS = frozenset(
    """
    about after all also an and any are as at be been before being between both but by
    can could did do does doing done during each few for from further had has have having
    he her here hers him his how if in into is it its just me more most my no nor not of
    off on once only or other our out over own same she should so some such than that the
    their them then there these they this those through to too under until up very was we
    were what when where which while who whom why will with would you your
    """.split()
)


def _ensure_vector_table(db: Session) -> bool:
    """True when the vector table is there to be written to.

    Created on demand as well as in the migration, so a deployment that
    gains the extension later starts indexing without a second migration.
    """
    if not vectors_available():
        return False
    try:
        db.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vectors USING vec0("
                f"chunk_id INTEGER PRIMARY KEY, embedding FLOAT[{EMBEDDING_DIMENSIONS}])"
            )
        )
        return True
    except OperationalError:
        return False


def fts_query(query: str) -> str | None:
    """A user's words as an FTS5 expression that cannot be a syntax error.

    FTS5 MATCH takes a query language -- bare punctuation, an unbalanced
    quote or a stray ``NEAR`` from someone's sentence is a crash, not a
    search. So the words are extracted and quoted individually, and joined
    with OR: recall is what matters here, since fusion does the ranking.
    """
    # Every term is quoted, which in FTS5 means "these tokens in this order".
    # That is what makes a dotted identifier work: the tokeniser still splits
    # "A.5.23" into a/5/23, but inside quotes they have to appear together.
    terms = [
        f'"{term}"'
        for term in _TERM.findall(query)
        if len(term) >= 2 and term.lower() not in _STOPWORDS
    ]
    if not terms:
        # Nothing but stopwords. Keyword search has nothing to say about it;
        # vector search still might, so this refuses rather than guesses.
        return None
    return " OR ".join(terms)


def clear_for_source(db: Session, source_type: str, source_id: int) -> None:
    """Remove every trace of one source from all three tables."""
    chunk_ids = list(
        db.scalars(
            select(DocumentChunk.id).where(
                DocumentChunk.source_type == source_type,
                DocumentChunk.source_id == source_id,
            )
        )
    )
    if not chunk_ids:
        return
    placeholders = ",".join(str(int(i)) for i in chunk_ids)
    db.execute(text(f"DELETE FROM document_chunks_fts WHERE rowid IN ({placeholders})"))
    if _ensure_vector_table(db):
        db.execute(text(f"DELETE FROM chunk_vectors WHERE chunk_id IN ({placeholders})"))
    db.execute(
        delete(DocumentChunk).where(
            DocumentChunk.source_type == source_type, DocumentChunk.source_id == source_id
        )
    )


def add_chunks(
    db: Session, chunks: list[DocumentChunk], vectors: list[list[float]] | None
) -> list[DocumentChunk]:
    """Insert chunks and their search entries as one unit.

    ``vectors`` is positional with ``chunks``; pass None when embeddings
    aren't available, and the rows are still keyword-searchable.
    """
    if not chunks:
        return []
    db.add_all(chunks)
    # Ids are needed to key the other two tables, so flush before writing them.
    db.flush()

    for chunk in chunks:
        db.execute(
            text("INSERT INTO document_chunks_fts(rowid, text) VALUES (:rowid, :text)"),
            {"rowid": chunk.id, "text": chunk.text},
        )

    if vectors and _ensure_vector_table(db):
        for chunk, vector in zip(chunks, vectors, strict=False):
            db.execute(
                text(
                    "INSERT INTO chunk_vectors(chunk_id, embedding) "
                    "VALUES (:chunk_id, :embedding)"
                ),
                {"chunk_id": chunk.id, "embedding": serialize(vector)},
            )
    return chunks


def keyword_ranked(db: Session, query: str, limit: int = CANDIDATES_PER_METHOD) -> list[int]:
    """Chunk ids by BM25, best first. Exact terms: control ids, proper nouns."""
    expression = fts_query(query)
    if expression is None:
        return []
    try:
        rows = db.execute(
            text(
                "SELECT rowid FROM document_chunks_fts "
                "WHERE document_chunks_fts MATCH :q ORDER BY rank LIMIT :limit"
            ),
            {"q": expression, "limit": limit},
        ).all()
    except OperationalError:
        return []
    return [row[0] for row in rows]


def vector_ranked(
    db: Session, vector: list[float] | None, limit: int = CANDIDATES_PER_METHOD
) -> list[tuple[int, float]]:
    """(chunk id, distance) by embedding, nearest first. Meaning, not words.

    The distance comes back with the id because retrieval needs it for the
    relevance floor: rank alone cannot say whether the nearest passage is
    actually near, and something is always nearest.
    """
    if not vector or not _ensure_vector_table(db):
        return []
    try:
        rows = db.execute(
            text(
                "SELECT chunk_id, distance FROM chunk_vectors "
                "WHERE embedding MATCH :v AND k = :limit ORDER BY distance"
            ),
            {"v": serialize(vector), "limit": limit},
        ).all()
    except OperationalError:
        return []
    return [(row[0], float(row[1])) for row in rows]


def fuse(*rankings: list[int]) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion over any number of ranked id lists.

    Each list contributes 1/(k + rank) per id. Ranks, not scores, so BM25's
    unbounded numbers and cosine distance never have to be made comparable
    -- which is the reason this is the standard way to combine them.
    """
    scores: dict[int, float] = {}
    for ranking in rankings:
        for position, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + position)
    return sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))


def chunks_by_id(db: Session, chunk_ids: list[int]) -> dict[int, DocumentChunk]:
    if not chunk_ids:
        return {}
    found = db.scalars(select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids)))
    return {chunk.id: chunk for chunk in found}
