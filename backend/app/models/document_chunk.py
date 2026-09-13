"""A passage of an uploaded document, as the assistant is allowed to see it.

Chunks are the unit of retrieval and the unit of citation: an answer names
the chunk it drew on, and that chunk names the file, the page and whether
the text was read directly or recovered by OCR. A reader can always get
back to the page a claim came from.

The text is duplicated into an FTS5 table and its embedding into a
sqlite-vec table, both keyed on this row's id -- see
``app/repositories/document_index_repository.py``, which owns every write to
all three so they cannot drift apart.
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChunkSource(StrEnum):
    """How the text was obtained, which is part of how far to trust it."""

    TEXT = "text"
    # Recovered from an image or a scanned page. Good enough to find a
    # document by, imperfect enough that a citation says so.
    OCR = "ocr"


class IndexStatus(StrEnum):
    """Whether the assistant can see a given piece of evidence.

    This is recorded per file and reported to the user, because the failure
    that matters most is the quiet one: a document that was never indexed
    looks exactly like a document with nothing relevant in it, and an
    assistant that cannot tell them apart will say "the record doesn't cover
    that" about evidence sitting right there.
    """

    PENDING = "pending"
    INDEXED = "indexed"
    # Read successfully, but there was no text in it -- a photo of a wall.
    EMPTY = "empty"
    # A format nothing here can read, or a file that failed to parse.
    UNREADABLE = "unreadable"


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), index=True
    )
    # Position within the document, so neighbouring passages can be shown
    # around a hit and citations read in a sensible order.
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    # "page 4", "Sheet: Controls", "3. Data Protection" -- whatever the
    # document's own structure calls this place, for the citation to quote.
    section: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source: Mapped[str] = mapped_column(String(10), default=ChunkSource.TEXT)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
