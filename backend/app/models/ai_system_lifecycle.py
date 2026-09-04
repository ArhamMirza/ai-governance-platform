from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.lifecycle_stages import LifecycleStage


class AISystemLifecycle(Base):
    """Where one AI system sits in its life cycle, plus the structured facts
    the stage gates check. One row per AI system (same sheet_rows FK the
    impact and risk assessments use).

    These fields live here rather than as inventory sheet columns so they are
    typed, server-owned, and can't be deleted by editing the grid."""

    __tablename__ = "ai_system_lifecycles"

    id: Mapped[int] = mapped_column(primary_key=True)
    ai_system_row_id: Mapped[int] = mapped_column(
        ForeignKey("sheet_rows.id"), unique=True, index=True
    )
    current_stage: Mapped[str] = mapped_column(String(40), default=LifecycleStage.INCEPTION)
    entered_stage_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Deployment record -- settable over the API so a CI/CD job can stamp it.
    deployment_environment: Mapped[str | None] = mapped_column(String(100), nullable=True)
    deployment_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    deployed_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Release sign-off, by someone other than whoever requested it.
    deployment_approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deployment_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Operation and monitoring.
    monitoring_owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    incident_escalation_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Retirement, and the archive it leaves behind. A retired system's record
    # is kept for retention_until so it stays auditable after the system is
    # switched off; only then can it be deleted.
    retirement_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    retirement_approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retirement_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retired_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    retention_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
