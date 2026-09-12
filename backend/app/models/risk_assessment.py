from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RiskAssessmentStatus(StrEnum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    PENDING_OWNER_APPROVAL = "pending_owner_approval"
    PENDING_CAIGO_APPROVAL = "pending_caigo_approval"
    COMPLETED = "completed"


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Unique: one risk assessment per AI system. create_risk_assessment says
    # so too, but its check and its insert are separate transactions, so the
    # constraint is what actually holds under two simultaneous requests.
    ai_system_row_id: Mapped[int] = mapped_column(
        ForeignKey("sheet_rows.id"), unique=True, index=True
    )
    sheet_id: Mapped[int] = mapped_column(ForeignKey("sheets.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=RiskAssessmentStatus.DRAFT)
    assessor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assessment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Same yearly cadence as ImpactAssessment (see app.core.review_cadence) so
    # the two assessments for one AI system stay aligned.
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Two-stage approval: the AI System Owner signs off first (skipped when
    # the owner is also the assessor), then the Chief AI Governance Officer
    # gives the final sign-off that moves status to COMPLETED.
    owner_approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    caigo_approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    caigo_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
