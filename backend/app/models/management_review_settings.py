from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ManagementReviewSettings(Base):
    """Whether management reviews recur, and on what interval -- a
    singleton, like RiskCriteria: one organization has one management
    review process (ISO/IEC 42001 Clause 9.3), not several. See
    management_review_service."""

    __tablename__ = "management_review_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # None = no schedule configured -- reviews are logged as they happen,
    # with no due-date tracking (the same "nothing to be due" state
    # AuditProgram's ad_hoc gets).
    interval_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Anchor for the first cycle, before any meeting has been recorded yet.
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
