from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditScheduleType(StrEnum):
    INTERVAL = "interval"
    AD_HOC = "ad_hoc"


class AuditProgramStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class AuditProgram(Base):
    """The plan for an internal audit -- ISO/IEC 42001 Clause 9.2. Fixed and
    independent, like Policy/Procedure, rather than a header wrapping a
    variable-column sheet: a program has no user-editable line items of its
    own, only the audits recorded against it (see InternalAudit).

    A recurring program's `next_due_date` (see internal_audit_service) is
    computed from its actual audit history, never stored -- it can't outlive
    the audit that set it, the same discipline every other overdue/next-due
    value in this codebase follows."""

    __tablename__ = "audit_programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    schedule_type: Mapped[str] = mapped_column(String(20), default=AuditScheduleType.INTERVAL)
    # Required (enforced at the schema level) when schedule_type is
    # "interval"; always null for an ad hoc program.
    interval_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Anchor for the first cycle, before any audit has been conducted yet.
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Bare nullable Integer, matching Policy.owner_id / CorrectiveAction.assignee_id
    # convention exactly -- no DB-level FK; resolved against users at read time.
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=AuditProgramStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
