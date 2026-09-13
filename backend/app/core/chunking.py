"""Splitting a document into passages worth retrieving.

The failure this is written against is over-fragmentation. A control and the
sentence that says whether it is implemented land in different chunks, each
one retrieves as weakly relevant, neither answers the question, and the
assistant reports nothing found. So boundaries follow the document's own
structure first and a size target second: a page, a sheet, a heading is a
wall, and packing happens inside those walls.

Sizes are in estimated tokens (characters/4 -- close enough for budgeting,
and it avoids dragging in a tokenizer whose vocabulary would have to match
whichever model the org picked).
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.models.document_chunk import ChunkSource

TARGET_TOKENS = 500
# Enough that a sentence split across a boundary is still whole in one of
# the two chunks, small enough not to bloat the index.
OVERLAP_TOKENS = 75
# Below this a chunk is a sliver -- a heading on its own, a page number --
# so it joins its neighbour rather than becoming a retrievable passage that
# can only ever be a false hit.
MIN_TOKENS = 25

_CHARS_PER_TOKEN = 4
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


@dataclass(frozen=True)
class Segment:
    """A structurally distinct piece of a document, as extraction found it."""

    text: str
    section: str | None = None
    source: ChunkSource = ChunkSource.TEXT


@dataclass(frozen=True)
class Chunk:
    text: str
    section: str | None
    source: ChunkSource
    ordinal: int
    token_estimate: int


def _split_on_words(text: str, limit: int) -> list[str]:
    """Break a run of text at whitespace, never through a token.

    A single token longer than the limit (a base64 blob, a hash) is the one
    case with no boundary to find, and it is cut on width.
    """
    pieces, current = [], ""
    for word in text.split():
        if len(word) > limit:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(word[i : i + limit] for i in range(0, len(word), limit))
        elif not current:
            current = word
        elif len(current) + 1 + len(word) <= limit:
            current = f"{current} {word}"
        else:
            pieces.append(current)
            current = word
    if current:
        pieces.append(current)
    return pieces


def _split_oversized(text: str) -> list[str]:
    """Break one over-long paragraph on the cleanest boundary available."""
    limit = TARGET_TOKENS * _CHARS_PER_TOKEN
    pieces, current = [], ""
    for sentence in _SENTENCE_END.split(text):
        if current and len(current) + len(sentence) + 1 > limit:
            pieces.append(current.strip())
            current = sentence
        elif len(sentence) > limit:
            # A single sentence longer than a whole chunk. Fall back to word
            # boundaries rather than raw width: cutting mid-token would split
            # a control id like "A.5.23" into two halves, and keyword search
            # -- the retriever that exists to find exactly those -- would
            # then match neither.
            if current.strip():
                pieces.append(current.strip())
            current = ""
            pieces.extend(_split_on_words(sentence, limit))
        else:
            current = f"{current} {sentence}".strip() if current else sentence
    if current.strip():
        pieces.append(current.strip())
    return [p for p in pieces if p]


def _tail_for_overlap(text: str) -> str:
    """The end of a chunk, repeated at the start of the next one.

    Cut back to a sentence boundary where there is one, so the overlap opens
    mid-thought as rarely as possible.
    """
    want = OVERLAP_TOKENS * _CHARS_PER_TOKEN
    if len(text) <= want:
        return text
    tail = text[-want:]
    sentences = _SENTENCE_END.split(tail, maxsplit=1)
    return sentences[1] if len(sentences) > 1 and sentences[1] else tail


def _pack(paragraphs: Sequence[str]) -> list[str]:
    """Fill chunks up to the target, carrying an overlap across each break."""
    limit = TARGET_TOKENS * _CHARS_PER_TOKEN
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if current and len(candidate) > limit:
            chunks.append(current)
            current = f"{_tail_for_overlap(current)}\n\n{paragraph}".strip()
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def chunk_segments(segments: Iterable[Segment]) -> list[Chunk]:
    """Passages for the whole document, numbered in reading order."""
    chunks: list[Chunk] = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue

        paragraphs: list[str] = []
        for raw in _PARAGRAPH_BREAK.split(text):
            paragraph = raw.strip()
            if not paragraph:
                continue
            if estimate_tokens(paragraph) > TARGET_TOKENS:
                paragraphs.extend(_split_oversized(paragraph))
            else:
                paragraphs.append(paragraph)

        for body in _pack(paragraphs):
            # A sliver joins the passage before it, as long as that passage
            # came from the same section -- the structural wall still holds.
            if (
                chunks
                and estimate_tokens(body) < MIN_TOKENS
                and chunks[-1].section == segment.section
                and chunks[-1].source == segment.source
            ):
                merged = f"{chunks[-1].text}\n\n{body}"
                chunks[-1] = Chunk(
                    text=merged,
                    section=chunks[-1].section,
                    source=chunks[-1].source,
                    ordinal=chunks[-1].ordinal,
                    token_estimate=estimate_tokens(merged),
                )
                continue
            chunks.append(
                Chunk(
                    text=body,
                    section=segment.section,
                    source=segment.source,
                    ordinal=len(chunks),
                    token_estimate=estimate_tokens(body),
                )
            )
    return chunks
