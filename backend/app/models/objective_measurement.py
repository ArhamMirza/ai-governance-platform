from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ObjectiveMeasurement(Base):
    """One reading of a measured objective's metric -- ISO/IEC 42001 9.1's
    documented evidence of monitoring results. Supporting files (a test
    report, an export) attach as evidence
    (entity_type="ObjectiveMeasurement")."""

    __tablename__ = "objective_measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    objective_id: Mapped[int] = mapped_column(ForeignKey("ai_objectives.id"), index=True)
    measured_on: Mapped[date] = mapped_column(Date)
    value: Mapped[float] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
