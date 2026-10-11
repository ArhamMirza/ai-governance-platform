from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChangeType(StrEnum):
    AI_SYSTEM = "ai_system"
    PROCESS = "process"
    POLICY = "policy"
    ORGANIZATION = "organization"
    OTHER = "other"


class ChangeStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    CANCELLED = "cancelled"


class ManagementSystemChange(Base):
    """A change to the AI management system, planned and carried out in a
    controlled way -- ISO/IEC 42001 6.3.

    A flat, fixed-schema record like AIObjective. Where it stands (planned,
    in progress, overdue ...) is computed live from these dates
    (app.core.change_tracking); only the status is a person's call."""

    __tablename__ = "management_system_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_type: Mapped[str] = mapped_column(String(20), default=ChangeType.OTHER)
    # 6.3: the purpose of the change and its potential consequences, and
    # what it needs.
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    consequences: Mapped[str | None] = mapped_column(Text, nullable=True)
    resources_needed: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Bare nullable Integer, like AIObjective.owner_id.
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # When it was raised -- a management review dated before this doesn't
    # list it.
    raised_on: Mapped[date] = mapped_column(Date)
    planned_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default=ChangeStatus.PLANNED)
    # Set when work starts and when it's closed, so a standing as of an
    # earlier date still sees it as it was.
    started_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    closure_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ChangeAISystem(Base):
    """An AI system a change affects. Removed (the change itself survives)
    when the AI system is deleted -- see change_service.unlink_ai_system."""

    __tablename__ = "management_system_change_ai_systems"
    __table_args__ = (
        UniqueConstraint("change_id", "ai_system_row_id", name="uq_change_ai_system"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    change_id: Mapped[int] = mapped_column(ForeignKey("management_system_changes.id"), index=True)
    ai_system_row_id: Mapped[int] = mapped_column(ForeignKey("sheet_rows.id"), index=True)
