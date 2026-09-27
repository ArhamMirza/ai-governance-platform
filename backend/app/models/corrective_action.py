from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CorrectiveActionStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_VERIFICATION = "pending_verification"
    CLOSED = "closed"


class CorrectiveAction(Base):
    """A nonconformity, tracked through root cause, corrective action, and a
    verified close -- ISO/IEC 42001 Clause 10.1/10.2.

    A flat, independent record like Policy/Procedure, not a header wrapping a
    variable-column sheet like RiskAssessment: a corrective action has no
    user-editable set of line items of its own, so a generic sheet would add
    indirection for nothing.
    """

    __tablename__ = "corrective_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    nonconformity_description: Mapped[str] = mapped_column(Text)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # What raised this -- a RiskItem sheet row, an ImpactAssessment, or
    # nothing (an internal-audit finding with no tracked record behind it).
    # Same (source_type, source_id) polymorphic pair as DocumentChunk: no FK,
    # since it can point at any of several tables, and it is optional because
    # not every nonconformity traces back to one specific existing record.
    source_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Bare nullable Integer, matching Policy.owner_id / AISystemLifecycle.owner_id
    # convention exactly -- no DB-level FK; resolved against users at read time.
    assignee_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default=CorrectiveActionStatus.OPEN)

    # Set once, on verify_and_close -- mirrors owner_approved_by/at.
    closed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
