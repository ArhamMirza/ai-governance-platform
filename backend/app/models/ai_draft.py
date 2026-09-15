"""A model's proposal for a whole record, held until a person decides on it.

The draft is kept on the server rather than passed through the browser, for
the audit trail's sake. When someone applies it, the server compares what
they are saving against what the model actually proposed -- so the log can
say, field by field, whether text was taken as drafted, edited first, or
turned down, without trusting the client to report that honestly. An auditor
asking "which parts of this assessment did a model write?" gets an answer
the application can stand behind.

A draft changes nothing on its own. It is text and scores sitting beside the
record; only the apply step writes, and it writes through the same service
functions -- and the same approval-withdrawal rules -- as a person typing.
"""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DraftStatus(StrEnum):
    READY = "ready"
    APPLIED = "applied"
    DISCARDED = "discarded"
    # A newer draft for the same record was generated. Kept, not deleted:
    # it is part of the record of what the model was asked and said.
    SUPERSEDED = "superseded"


class AiDraft(Base):
    __tablename__ = "ai_drafts"
    __table_args__ = (Index("ix_ai_drafts_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(15), default=DraftStatus.READY)
    requested_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Which model wrote it -- recorded at the time, because the organisation's
    # configured provider can change later and the draft's provenance must not.
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(100))
    # One entry per proposed field: its value, the sources it cites, and a
    # stated gap where the records did not support drafting it.
    proposals: Mapped[list] = mapped_column(JSON, default=list)
    # The numbered sources the proposals cite, as they were at drafting time.
    sources: Mapped[list] = mapped_column(JSON, default=list)
    injection_findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    coverage_gaps: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Filled in when applied: what was accepted, edited and rejected.
    decisions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    applied_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
