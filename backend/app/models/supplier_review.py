from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SupplierReviewOutcome(StrEnum):
    SATISFACTORY = "satisfactory"
    CONCERNS = "concerns"
    UNSATISFACTORY = "unsatisfactory"


class SupplierReview(Base):
    """One periodic review of a supplier. Supporting documents (a
    questionnaire, an audit report, a SOC 2) attach as evidence
    (entity_type="SupplierReview"). The latest review sets when the next is
    due -- see app.core.supplier_schedule."""

    __tablename__ = "supplier_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    review_date: Mapped[date] = mapped_column(Date)
    outcome: Mapped[str] = mapped_column(String(20), default=SupplierReviewOutcome.SATISFACTORY)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
