"""Scoring how well a passage actually answers a query, once retrieval has
already narrowed the field.

BM25 and the bi-encoder embedding each score a passage against the query
independently -- a passage vector and a query vector are compared, but
neither ever looks at the other's actual words. Two passages that share
vocabulary with the query can end up ranked alike even when only one of
them actually answers it. A cross-encoder reads the query and the passage
together, with real attention between the two, which is the one signal
neither retriever has.

That joint scoring is too slow to run over a whole corpus -- it is only
applied to the already-fused, already-filtered top of the list retrieval
service hands it (RERANK_CANDIDATES in retrieval_service.py), where scoring
a few dozen short passages costs milliseconds on the CPU.

Local, like the embedder, and for the same reason: a passage a governance
platform holds is exactly the kind of material that should not be sent to
a third party just to rank it. MiniLM-L-6-v2 tuned for re-ranking (trained
on MS MARCO) is the standard lightweight choice for this -- about 80MB,
versus several hundred MB to over a gigabyte for the larger rerankers
fastembed also ships.
"""

import threading
from collections.abc import Sequence

MODEL_NAME = "Xenova/ms-marco-MiniLM-L-6-v2"

_model = None
_unavailable_reason: str | None = None
# Loaded once per process; see embeddings.py for why this lock exists --
# without it, requests arriving together while the model loads would each
# start their own ONNX session and all but one would be thrown away.
_load_lock = threading.Lock()


def _load():
    """The reranking model, or None if it can't be loaded here."""
    global _model, _unavailable_reason
    if _model is not None or _unavailable_reason is not None:
        return _model
    with _load_lock:
        if _model is not None or _unavailable_reason is not None:
            return _model
        try:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            _model = TextCrossEncoder(model_name=MODEL_NAME)
        except Exception as exc:  # noqa: BLE001 -- a missing wheel, no disk, no network on first run
            # Recorded rather than raised: without a reranker, results keep
            # their fusion order, which is worse but not broken.
            _unavailable_reason = f"{type(exc).__name__}: {exc}"
            return None
    return _model


def warm() -> None:
    """Load the model now, so no search pays for it. Safe to call repeatedly."""
    _load()


def available() -> bool:
    return _load() is not None


def unavailable_reason() -> str | None:
    _load()
    return _unavailable_reason


def rerank(query: str, passages: Sequence[str]) -> list[float] | None:
    """A relevance score per passage, in the order given -- higher means more
    relevant to ``query``. None if the model can't be loaded here, so a
    caller can fall back to whatever ranking it already had."""
    model = _load()
    if model is None or not passages:
        return None
    return [float(score) for score in model.rerank(query, list(passages))]


def reset_for_tests() -> None:
    """Drop the cached model so a test can install its own in place."""
    global _model, _unavailable_reason
    _model, _unavailable_reason = None, None
