from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RiskAssessmentStatus(StrEnum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ai_system_row_id: Mapped[int] = mapped_column(ForeignKey("sheet_rows.id"), index=True)
    sheet_id: Mapped[int] = mapped_column(ForeignKey("sheets.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=RiskAssessmentStatus.DRAFT)
    assessor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assessment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Same yearly cadence as ImpactAssessment (see app.core.review_cadence) so
    # the two assessments for one AI system stay aligned.
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
