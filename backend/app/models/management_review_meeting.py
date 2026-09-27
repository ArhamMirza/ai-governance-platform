from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ManagementReviewMeeting(Base):
    """One top-management review meeting -- ISO/IEC 42001 Clause 9.3. Flat
    and independent, like Policy/CorrectiveAction, not a header wrapping a
    sheet: a meeting has no user-editable line items of its own.

    One field per clause 9.3 input/output, so the record is a checklist of
    what the standard requires reviewing and deciding, not one
    undifferentiated notes blob."""

    __tablename__ = "management_review_meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_date: Mapped[date] = mapped_column(Date)
    # Bare nullable Integer, matching assignee_id/auditor_id convention.
    chaired_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Free text, not a list of user ids -- not every attendee (an external
    # auditor, a board member) necessarily has an account here.
    attendees: Mapped[str | None] = mapped_column(Text, nullable=True)

    previous_actions_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_changes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Nonconformities/corrective actions, monitoring results, audit
    # results, achievement of AI objectives.
    performance_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    stakeholder_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_adequacy: Mapped[str | None] = mapped_column(Text, nullable=True)
    improvement_opportunities: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The output: decisions, actions, and resource/AIMS changes agreed.
    decisions_and_actions: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
