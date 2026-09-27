from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InternalAuditStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class InternalAudit(Base):
    """One actual audit occurrence under an AuditProgram. A real FK, not the
    polymorphic (source_type, source_id) pair CorrectiveAction uses --
    unlike a corrective action's source (which can be any of several kinds
    of record), an audit's parent program is always exactly one thing, so a
    real foreign key is the honest relationship."""

    __tablename__ = "internal_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    audit_program_id: Mapped[int] = mapped_column(ForeignKey("audit_programs.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    planned_date: Mapped[date] = mapped_column(Date)
    conducted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Bare nullable Integer, matching assignee_id/owner_id convention.
    auditor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=InternalAuditStatus.PLANNED)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
