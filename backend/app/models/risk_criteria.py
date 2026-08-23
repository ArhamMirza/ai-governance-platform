from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Scores are likelihood x impact on a 1..5 scale, so they run 1..25.
MIN_SCORE = 1
MAX_SCORE = 25

# Defaults used until an organization sets its own risk appetite. High starts at
# 13 because that is where a 5x5 matrix cell first shades red.
DEFAULT_MEDIUM_MIN_SCORE = 5
DEFAULT_HIGH_MIN_SCORE = 13


class RiskCriteria(Base):
    """Organization-wide risk appetite. A single row; see risk_criteria_service."""

    __tablename__ = "risk_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medium_min_score: Mapped[int] = mapped_column(Integer, default=DEFAULT_MEDIUM_MIN_SCORE)
    high_min_score: Mapped[int] = mapped_column(Integer, default=DEFAULT_HIGH_MIN_SCORE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
