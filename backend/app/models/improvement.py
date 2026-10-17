from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ImprovementSource(StrEnum):
    """Where the opportunity came from -- a category, so one with no record
    behind it (an idea, a stakeholder's remark) still says where it arose."""

    INTERNAL_AUDIT = "internal_audit"
    MANAGEMENT_REVIEW = "management_review"
    CONCERN = "concern"
    INCIDENT = "incident"
    CORRECTIVE_ACTION = "corrective_action"
    OBJECTIVE = "objective"
    STAKEHOLDER_FEEDBACK = "stakeholder_feedback"
    IDEA = "idea"
    OTHER = "other"


class ImprovementStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    IMPLEMENTED = "implemented"
    DECLINED = "declined"


class Improvement(Base):
    """An opportunity to improve the AI management system, and what came of
    it -- ISO/IEC 42001 10.1. Nonconformities go to CorrectiveAction (10.2);
    this is for what could be better rather than what went wrong.

    A flat, fixed-schema record like ManagementSystemChange. Where it stands
    (proposed, accepted, overdue ...) is computed live from these dates
    (app.core.improvement_tracking); only the status is a person's call."""

    __tablename__ = "improvements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_benefit: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(30), default=ImprovementSource.OTHER)
    # The record it arose from, when there is one. Same (source_type,
    # source_id) polymorphic pair as CorrectiveAction: no FK, since it can
    # point at any of several tables.
    source_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Bare nullable Integer, like ManagementSystemChange.owner_id.
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    raised_on: Mapped[date] = mapped_column(Date)
    target_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default=ImprovementStatus.PROPOSED)
    # Set when it's accepted and when it's closed, so a standing as of an
    # earlier date still sees it as it was.
    decided_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    # What changed and whether it worked -- required to mark it implemented,
    # and the evidence 10.1 asks for.
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    decline_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The planned change (6.3) it's being carried out as, if any. Cleared
    # when that change is deleted -- see improvement_service.unlink_change.
    change_id: Mapped[int | None] = mapped_column(
        ForeignKey("management_system_changes.id"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
