from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ImpactAssessmentStatus(StrEnum):
    DRAFT = "draft"
    PENDING_OWNER_APPROVAL = "pending_owner_approval"
    PENDING_CAIGO_APPROVAL = "pending_caigo_approval"
    COMPLETED = "completed"


class ImpactAssessment(Base):
    """An ISO 42001 clause 8.4 / Annex A.5 impact assessment, structured per
    ISO/IEC 42005's guidance. Scoped to one AI system (ai_system_row_id, the
    same sheet_rows FK RiskAssessment uses) rather than to a single Risk
    Assessment run -- a system can be re-assessed several times over its
    lifecycle, and every risk assessment for that system shares the same
    impact history rather than each owning a private copy."""

    __tablename__ = "impact_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Unique for the same reason RiskAssessment.ai_system_row_id is: the
    # "one per AI system" rule above is checked in a transaction of its own,
    # so only the constraint survives two simultaneous requests.
    ai_system_row_id: Mapped[int] = mapped_column(
        ForeignKey("sheet_rows.id"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default=ImpactAssessmentStatus.DRAFT)
    assessor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assessment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Set from assessment_date on completion (see app.core.review_cadence) --
    # ISO 42001 expects assessments to be re-performed at planned intervals.
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

    system_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    intended_purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    foreseeable_misuse: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_and_model_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    deployment_environment: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_interested_parties: Mapped[str | None] = mapped_column(Text, nullable=True)
    human_oversight_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
