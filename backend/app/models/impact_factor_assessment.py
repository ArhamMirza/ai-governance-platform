from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ImpactFactorAssessment(Base):
    """One of the eight ISO/IEC 42005 impact dimensions (see
    app.core.impact_factors.IMPACT_FACTORS) scored within a single
    ImpactAssessment. Exactly one row per factor is seeded when the
    ImpactAssessment is created -- this is a fixed scorecard, not a
    user-managed list.

    benefits/harms are the evidence the user writes up before assigning a
    score; a future auto-scoring pass will derive `score` from
    benefits/harms/criteria instead of requiring it to be typed by hand."""

    __tablename__ = "impact_factor_assessments"
    __table_args__ = (
        UniqueConstraint("impact_assessment_id", "factor", name="uq_impact_factor_once"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    impact_assessment_id: Mapped[int] = mapped_column(
        ForeignKey("impact_assessments.id"), index=True
    )
    factor: Mapped[str] = mapped_column(String(50))
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    harms: Mapped[str | None] = mapped_column(Text, nullable=True)
    criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
