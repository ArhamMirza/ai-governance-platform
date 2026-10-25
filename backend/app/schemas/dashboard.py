from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.compliance_status import ComplianceStatusSummary
from app.schemas.risk_criteria import RiskCriteriaRead


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


class RiskItemSummary(BaseModel):
    """Aggregates across every individual risk item in every assessment."""

    total: int
    by_severity: dict[str, int]
    overdue_count: int
    untreated_count: int
    average_inherent_score: float | None
    average_residual_score: float | None


class MatrixCell(BaseModel):
    likelihood: int
    impact: int
    count: int


class CoverageSummary(BaseModel):
    """Governance coverage ratios, expressed as assessed/total pairs."""

    ai_systems_total: int
    ai_systems_assessed: int
    # Impact assessment precedes risk assessment, so this is tracked
    # separately -- a system can be impact-assessed but not yet risk-assessed.
    ai_systems_impact_assessed: int
    assessments_review_overdue: int
    policies_total: int
    policies_approved: int
    procedures_total: int
    procedures_approved: int


class AttentionItem(BaseModel):
    key: str
    label: str
    count: int
    severity: str
    # The area it belongs to; items arrive already ordered so each area's
    # items are contiguous -- see dashboard_service._order_attention.
    group: str


class MyRiskItem(BaseModel):
    """One open risk item owned by the requesting user, for the "My Risk
    Items" dashboard panel -- lets an owner see what they're on the hook
    for without opening every assessment."""

    risk_assessment_id: int
    row_id: int
    category: str | None
    description: str | None
    status: str | None
    treatment_deadline: str | None
    overdue: bool


class MyCorrectiveActionItem(BaseModel):
    """One open corrective action assigned to the requesting user, for the
    "My Corrective Actions" dashboard panel -- the same shape as MyRiskItem."""

    id: int
    title: str
    status: str
    due_date: date
    overdue: bool


class MyTrainingItem(BaseModel):
    """One competence requirement the requesting user hasn't met -- never
    completed, or lapsed -- for the "My Training" dashboard panel."""

    requirement_id: int
    title: str
    status: str
    next_due: date | None


class PendingApprovalItem(BaseModel):
    """One record currently waiting on the requesting user's approval,
    across every entity type that has an approval gate."""

    entity_type: str
    entity_id: int
    title: str
    stage_label: str
    submitted_at: datetime | None


class DashboardSummary(BaseModel):
    policies: StatusCounts
    procedures: StatusCounts
    ai_systems: AISystemSummary
    risk_assessments: RiskAssessmentSummary
    risk_items: RiskItemSummary
    coverage: CoverageSummary
    compliance: ComplianceStatusSummary
    attention: list[AttentionItem]
    matrix: list[MatrixCell]
    # Bundled so the client shades the matrix with the same bands used to count.
    criteria: RiskCriteriaRead
    my_risk_items: list[MyRiskItem]
    my_corrective_actions: list[MyCorrectiveActionItem]
    my_training: list[MyTrainingItem]
    pending_approvals: list[PendingApprovalItem]


class GettingStartedStep(BaseModel):
    """One thing to do when setting the platform up, and whether the records say
    it has been done."""

    key: str
    title: str
    why: str
    href: str
    done: bool
    optional: bool = False


class GettingStarted(BaseModel):
    steps: list[GettingStartedStep]
    done_count: int
    total: int
    # Every step that is not optional is done.
    complete: bool
    # The first step still to do, in the order a person would take them.
    next_key: str | None
