from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.risk_assessment import RiskAssessmentStatus


class RiskAssessmentCreate(BaseModel):
    ai_system_row_id: int
    framework_tags: list[str] = []
    assessor_id: int | None = None
    assessment_date: date | None = None


class RiskAssessmentUpdate(BaseModel):
    framework_tags: list[str] | None = None
    status: RiskAssessmentStatus | None = None
    assessor_id: int | None = None
    assessment_date: date | None = None


class RiskAssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ai_system_row_id: int
    sheet_id: int
    framework_tags: list[str]
    status: RiskAssessmentStatus
    assessor_id: int | None
    assessment_date: date | None
    overall_risk_rating: float | None
    created_at: datetime
    updated_at: datetime
