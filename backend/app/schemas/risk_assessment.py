from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.risk_assessment import RiskAssessmentStatus
from app.schemas.dashboard import MatrixCell, RiskItemSummary
from app.schemas.framework_control import FrameworkControlRead
from app.schemas.risk_criteria import RiskCriteriaRead


class RiskAssessmentCreate(BaseModel):
    ai_system_row_id: int
    assessor_id: int | None = None
    assessment_date: date | None = None


class RiskAssessmentUpdate(BaseModel):
    """status may only move between draft and in_progress here -- reaching
    pending_owner_approval, pending_caigo_approval or completed goes through
    the dedicated submit/approve endpoints instead, which is where the
    accountable person for each stage is actually checked."""

    status: RiskAssessmentStatus | None = None
    assessor_id: int | None = None
    assessment_date: date | None = None


class RiskAssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ai_system_row_id: int
    sheet_id: int
    # Framework tags are looked up separately (see framework_service) --
    # not a real ORM attribute, so from_attributes can't populate it.
    framework_tags: list[FrameworkControlRead]
    status: RiskAssessmentStatus
    assessor_id: int | None
    assessment_date: date | None
    next_review_date: date | None
    review_overdue: bool
    overall_risk_rating: float | None
    owner_approved_by: int | None
    owner_approved_at: datetime | None
    caigo_approved_by: int | None
    caigo_approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RiskAssessmentStats(BaseModel):
    """Per-assessment roll-up used by the portfolio table."""

    id: int
    ai_system_row_id: int
    status: RiskAssessmentStatus
    overall_risk_rating: float | None
    item_count: int
    high_count: int
    medium_count: int
    low_count: int
    overdue_count: int


class RiskPortfolioSummary(BaseModel):
    total_assessments: int
    by_status: dict[str, int]
    high_risk_count: int
    risk_items: RiskItemSummary
    matrix: list[MatrixCell]
    assessments: list[RiskAssessmentStats]
    # Bundled so the client shades the matrix with the same bands used to count.
    criteria: RiskCriteriaRead
