"""A passage of the record, as the assistant is allowed to see it.

Chunks are the unit of retrieval and the unit of citation: an answer names
the chunk it drew on, and that chunk names where it came from -- the file
and page, or the record and field -- and whether the text was read directly
or recovered by OCR. A reader can always get back to what a claim rests on.

A chunk carries two identities, because they answer different questions.
``source_*`` is what this passage *is*: evidence file 12, policy 3, the AI
system inventory row 7. ``entity_*`` is what it is *about*: a document
uploaded against a policy is a different thing from the policy, but a search
for everything known about that policy has to return both.

The text is duplicated into an FTS5 table and its embedding into a
sqlite-vec table, both keyed on this row's id -- see
``app/repositories/document_index_repository.py``, which owns every write to
all three so they cannot drift apart.
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Integer, String, Text
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


class SourceType(StrEnum):
    """What a chunk was made from.

    The names match the ``entity_type`` vocabulary evidence and folders
    already use, so one string means the same thing everywhere.
    """

    EVIDENCE = "Evidence"
    POLICY = "Policy"
    PROCEDURE = "Procedure"
    IMPACT_ASSESSMENT = "ImpactAssessment"
    AI_SYSTEM = "AISystem"
    DATA_INVENTORY = "DataInventory"
    RISK_ITEM = "RiskItem"


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # What this passage is. No foreign key: a chunk can come from any of
    # seven tables, and one nullable key per table would be worse than a
    # pair of columns that says plainly which one it means.
    source_type: Mapped[str] = mapped_column(String(30), index=True)
    source_id: Mapped[int] = mapped_column(Integer, index=True)
    # Denormalised so a citation can name its source without joining seven
    # tables at search time. Rewritten whenever the source is reindexed,
    # which is every time the source changes.
    source_title: Mapped[str] = mapped_column(String(300), default="")
    # What this passage is about -- for evidence, the record it was uploaded
    # against; for a record, itself. This is what scoping a search to one AI
    # system searches on.
    entity_type: Mapped[str] = mapped_column(String(30), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    # Position within the document, so neighbouring passages can be shown
    # around a hit and citations read in a sensible order.
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    # "page 4", "Sheet: Controls", "3. Data Protection" -- whatever the
    # document's own structure calls this place, for the citation to quote.
    section: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source: Mapped[str] = mapped_column(String(10), default=ChunkSource.TEXT)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0)
    # Text in this passage written to instruct a model. Held per passage, so
    # retrieval can surface the finding with the citation that carries it,
    # whatever kind of source it came from.
    injection_findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
