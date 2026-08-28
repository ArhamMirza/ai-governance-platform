from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.impact_assessment import ImpactAssessmentStatus
from app.schemas.framework_control import FrameworkControlRead


class ImpactAssessmentCreate(BaseModel):
    assessor_id: int | None = None
    assessment_date: date | None = None


class ImpactAssessmentUpdate(BaseModel):
    status: ImpactAssessmentStatus | None = None
    assessor_id: int | None = None
    assessment_date: date | None = None
    system_description: str | None = None
    intended_purpose: str | None = None
    foreseeable_misuse: str | None = None
    data_and_model_info: str | None = None
    deployment_environment: str | None = None
    affected_interested_parties: str | None = None
    human_oversight_role: str | None = None
    conclusion: str | None = None


class ImpactFactorAssessmentUpdate(BaseModel):
    benefits: str | None = None
    harms: str | None = None
    criteria: str | None = None
    score: int | None = None


class ImpactFactorAssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    factor: str
    benefits: str | None
    harms: str | None
    criteria: str | None
    score: int | None


class ImpactAssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ai_system_row_id: int
    status: ImpactAssessmentStatus
    assessor_id: int | None
    assessment_date: date | None
    system_description: str | None
    intended_purpose: str | None
    foreseeable_misuse: str | None
    data_and_model_info: str | None
    deployment_environment: str | None
    affected_interested_parties: str | None
    human_oversight_role: str | None
    conclusion: str | None
    created_at: datetime
    updated_at: datetime
    # Looked up separately (see framework_service/impact_factor_repository),
    # not real ORM attributes -- from_attributes can't populate these.
    framework_tags: list[FrameworkControlRead]
    factors: list[ImpactFactorAssessmentRead]
