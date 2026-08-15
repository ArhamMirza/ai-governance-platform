from pydantic import BaseModel


class StatusCounts(BaseModel):
    total: int
    by_status: dict[str, int]


class AISystemSummary(BaseModel):
    total: int
    by_risk_tier: dict[str, int]


class RiskAssessmentSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    high_risk_count: int


class DashboardSummary(BaseModel):
    policies: StatusCounts
    procedures: StatusCounts
    ai_systems: AISystemSummary
    risk_assessments: RiskAssessmentSummary
