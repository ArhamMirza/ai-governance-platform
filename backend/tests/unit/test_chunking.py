"""How a document is cut into retrievable passages.

The bug these guard against is over-fragmentation: a control and the sentence
saying whether it is implemented landing in different chunks, so neither
answers the question and the assistant reports nothing found.
"""

from app.core.chunking import (
    MIN_TOKENS,
    OVERLAP_TOKENS,
    TARGET_TOKENS,
    Chunk,
    Segment,
    chunk_segments,
    estimate_tokens,
)
from app.models.document_chunk import ChunkSource


def long_text(words: str, tokens: int) -> str:
    return (words + " ") * (tokens * 4 // len(words))


def test_a_short_document_stays_one_passage() -> None:
    chunks = chunk_segments([Segment(text="The retention period is 24 months.")])

    assert len(chunks) == 1
    assert chunks[0].text == "The retention period is 24 months."


def test_structure_is_a_wall_that_packing_never_crosses() -> None:
    """Page 2's text must not be glued onto page 1's passage, however much
    room is left -- a citation that says "page 1" has to mean page 1."""
    chunks = chunk_segments(
        [
            Segment(text="Access control is reviewed quarterly.", section="page 1"),
            Segment(text="Retention is 24 months.", section="page 2"),
        ]
    )

    assert [c.section for c in chunks] == ["page 1", "page 2"]
    assert "Retention" not in chunks[0].text


def test_a_long_section_is_split_and_the_pieces_overlap() -> None:
    """Overlap is what keeps a sentence spanning a boundary whole in at
    least one of the two passages."""
    body = "\n\n".join(long_text("control statement", TARGET_TOKENS // 3) for _ in range(6))
    chunks = chunk_segments([Segment(text=body, section="page 1")])

    assert len(chunks) > 1
    assert all(c.token_estimate <= TARGET_TOKENS * 1.2 for c in chunks)
    # The second passage opens with text the first one ended with.
    assert chunks[1].text[:40].strip() in chunks[0].text


def test_a_paragraph_longer_than_a_whole_chunk_is_still_split() -> None:
    """No paragraph break to cut on, so it falls back to sentences."""
    body = " ".join(f"Sentence number {n} about governance." for n in range(400))
    chunks = chunk_segments([Segment(text=body)])

    assert len(chunks) > 1
    assert all(c.token_estimate <= TARGET_TOKENS * 1.2 for c in chunks)


def test_one_unbroken_sentence_is_split_on_width_without_losing_words() -> None:
    """No paragraph break and no sentence end to cut on: it splits on width
    and accepts the seam. What it must not do is drop anything."""
    words = [f"w{n}" for n in range(2000)]
    chunks = chunk_segments([Segment(text=" ".join(words))])

    assert len(chunks) > 1
    combined = " ".join(c.text for c in chunks)
    assert all(word in combined for word in words)


def test_a_sliver_joins_its_neighbour_rather_than_becoming_a_passage() -> None:
    """A heading or a page number alone is never the answer to anything, and
    as its own passage it can only ever be a false hit."""
    body = long_text("substantive governance content", TARGET_TOKENS // 2)
    chunks = chunk_segments([Segment(text=f"{body}\n\n3.1", section="page 1")])

    assert len(chunks) == 1
    assert chunks[0].text.endswith("3.1")


def test_a_sliver_in_a_new_section_is_kept_rather_than_merged_backwards() -> None:
    """Merging it would move text across a structural wall and mislabel it."""
    chunks = chunk_segments(
        [
            Segment(text=long_text("content", TARGET_TOKENS // 2), section="page 1"),
            Segment(text="Signed.", section="page 2"),
        ]
    )

    assert [c.section for c in chunks] == ["page 1", "page 2"]
    assert estimate_tokens(chunks[1].text) < MIN_TOKENS


def test_empty_and_whitespace_segments_produce_nothing() -> None:
    assert chunk_segments([Segment(text="   \n\n  "), Segment(text="")]) == []


def test_ordinals_run_in_reading_order_across_sections() -> None:
    chunks = chunk_segments(
        [
            Segment(text="First page text here.", section="page 1"),
            Segment(text="Second page text here.", section="page 2"),
            Segment(text="Third page text here.", section="page 3"),
        ]
    )

    assert [c.ordinal for c in chunks] == [0, 1, 2]


def test_the_source_of_the_text_survives_chunking() -> None:
    """Whether a passage was read or recovered by OCR has to reach the
    citation, so a reader knows a quote came from a picture of a page."""
    chunks = chunk_segments(
        [Segment(text="Scanned approval text.", section="page 1", source=ChunkSource.OCR)]
    )

    assert chunks[0].source == ChunkSource.OCR


def test_overlap_is_bounded_so_the_index_does_not_bloat() -> None:
    body = "\n\n".join(long_text("governance", TARGET_TOKENS // 2) for _ in range(4))
    chunks = chunk_segments([Segment(text=body)])

    assert isinstance(chunks[0], Chunk)
    total = sum(c.token_estimate for c in chunks)
    original = estimate_tokens(body)
    # Overlap costs roughly OVERLAP_TOKENS per boundary and nothing more.
    assert total <= original + OVERLAP_TOKENS * len(chunks) * 1.5
