"""Turning text into vectors, on this machine.

The model is a small ONNX one (BAAI/bge-small-en-v1.5, 384 dimensions) run
on the CPU by fastembed. That choice is deliberate rather than incidental:
an embedding API would mean every uploaded document -- the exact material a
governance platform holds because it is sensitive -- being sent to a third
party at index time, which would quietly break the promise the settings page
makes to anyone running a self-hosted model.

The model is loaded on first use, not at import, so an operator who never
turns document search on never pays for it.

Callers go through ``embed_passages`` and ``embed_query``. Those two are not
interchangeable: BGE models are trained with an instruction prefix on the
query side, and using the wrong one costs real retrieval accuracy.
"""

from collections.abc import Sequence

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIMENSIONS = 384

# What BGE expects in front of a search query. Passages get no prefix.
_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

_model = None
_unavailable_reason: str | None = None


def _load():
    """The embedding model, or None if it can't be loaded here."""
    global _model, _unavailable_reason
    if _model is not None or _unavailable_reason is not None:
        return _model
    try:
        from fastembed import TextEmbedding

        _model = TextEmbedding(model_name=MODEL_NAME)
    except Exception as exc:  # noqa: BLE001 -- a missing wheel, no disk, no network on first run
        # Recorded rather than raised: without vectors, search falls back to
        # keywords, which is worse but not broken.
        _unavailable_reason = f"{type(exc).__name__}: {exc}"
        return None
    return _model


def available() -> bool:
    return _load() is not None


def unavailable_reason() -> str | None:
    _load()
    return _unavailable_reason


def embed_passages(texts: Sequence[str]) -> list[list[float]]:
    """Vectors for document chunks, in the order given."""
    model = _load()
    if model is None or not texts:
        return []
    return [list(map(float, v)) for v in model.embed(list(texts))]


def embed_query(text: str) -> list[float] | None:
    """The vector for a search query, with the instruction prefix BGE wants."""
    model = _load()
    if model is None:
        return None
    vectors = [list(map(float, v)) for v in model.embed([_QUERY_INSTRUCTION + text])]
    return vectors[0] if vectors else None


def reset_for_tests() -> None:
    """Drop the cached model so a test can install its own in place."""
    global _model, _unavailable_reason
    _model, _unavailable_reason = None, None
