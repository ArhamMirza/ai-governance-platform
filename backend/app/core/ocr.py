"""Reading text out of images, on this machine.

Evidence in a governance platform is often a picture: a photographed sign-off
sheet, a screenshot of a configuration screen, a scanned certificate. Without
this, all of it indexes as empty -- and an empty document is indistinguishable
from an irrelevant one, so the assistant would answer "the record doesn't
cover that" about a signed approval sitting in the folder. A confident wrong
answer is the worst outcome available here, so the text gets recovered.

RapidOCR runs an ONNX model on the CPU. Like the embedder, nothing leaves the
deployment, and it loads on first use rather than at import.

What it is good at: printed text, screenshots, clean scans. What it is not:
handwriting, and the meaning of charts and diagrams. Text recovered here is
marked ``ChunkSource.OCR`` all the way through to the citation, so a reader
is told when a quote came from a picture of a page rather than the page.
"""

_engine = None
_unavailable_reason: str | None = None

# Below this, a "successful" read is almost always noise off a photograph
# rather than text anyone wrote.
MIN_CONFIDENCE = 0.5


def _load():
    global _engine, _unavailable_reason
    if _engine is not None or _unavailable_reason is not None:
        return _engine
    try:
        from rapidocr_onnxruntime import RapidOCR

        _engine = RapidOCR()
    except Exception as exc:  # noqa: BLE001 -- missing wheel, no disk for models
        _unavailable_reason = f"{type(exc).__name__}: {exc}"
        return None
    return _engine


def available() -> bool:
    return _load() is not None


def read_image(data: bytes) -> str:
    """Whatever printed text is legible in an image. Empty if there is none."""
    engine = _load()
    if engine is None:
        return ""
    try:
        result, _elapsed = engine(data)
    except Exception:  # noqa: BLE001 -- a corrupt or unsupported image is not fatal
        return ""
    if not result:
        return ""

    lines = [
        str(text).strip()
        for _box, text, score in result
        if str(text).strip() and float(score) >= MIN_CONFIDENCE
    ]
    return "\n".join(lines)


def reset_for_tests() -> None:
    global _engine, _unavailable_reason
    _engine, _unavailable_reason = None, None
