from collections import Counter

from sqlalchemy.orm import Session

from app.core import risk_scoring
from app.models.sheet import SheetRow
from app.repositories import (
    policy_repository,
    procedure_repository,
    risk_assessment_repository,
    sheet_repository,
)
from app.schemas.dashboard import (
    AISystemSummary,
    AttentionItem,
    CoverageSummary,
    DashboardSummary,
    RiskAssessmentSummary,
    StatusCounts,
)
from app.services import (
    ai_system_inventory_service,
    risk_analytics_service,
    risk_criteria_service,
)

APPROVED_STATUS = "approved"
IN_REVIEW_STATUS = "in_review"
HIGH_RISK_TIER = "high"


def _attention(
    *,
    overdue_count: int,
    unassessed_count: int,
    in_review_count: int,
    high_risk_count: int,
) -> list[AttentionItem]:
    """Actionable items, most urgent first. Zero-count items are dropped so the
    panel only ever shows things that need doing."""
    candidates = [
        AttentionItem(
            key="overdue_treatments",
            label="Risk treatments overdue",
            count=overdue_count,
            severity="danger",
        ),
        AttentionItem(
            key="unassessed_ai_systems",
            label="AI systems without a risk assessment",
            count=unassessed_count,
            severity="danger",
        ),
        AttentionItem(
            key="high_risk_assessments",
            label="Assessments rated high risk",
            count=high_risk_count,
            severity="warning",
        ),
        AttentionItem(
            key="awaiting_review",
            label="Policies and procedures awaiting review",
            count=in_review_count,
            severity="warning",
        ),
    ]
    return [item for item in candidates if item.count > 0]


def get_summary(db: Session) -> DashboardSummary:
    policies = policy_repository.list_all(db)
    procedures = procedure_repository.list_all(db)
    ai_system_rows = ai_system_inventory_service.list_rows(db)
    risk_assessments = risk_assessment_repository.list_all(db)

    # One query for every assessment's risk items instead of one per assessment.
    rows_by_sheet = sheet_repository.list_rows_for_sheets(
        db, [risk_assessment.sheet_id for risk_assessment in risk_assessments]
    )
    all_risk_rows: list[SheetRow] = [row for rows in rows_by_sheet.values() for row in rows]

    bands = risk_criteria_service.get_bands(db)

    high_risk_count = 0
    for risk_assessment in risk_assessments:
        rating = risk_analytics_service.overall_rating(
            rows_by_sheet.get(risk_assessment.sheet_id, [])
        )
        if rating is not None and risk_scoring.is_high_risk(rating, bands):
            high_risk_count += 1

    risk_tier_counts = Counter(
        str(row.data["risk_tier"]) if row.data.get("risk_tier") else "unspecified"
        for row in ai_system_rows
    )

    assessed_row_ids = {
        risk_assessment.ai_system_row_id for risk_assessment in risk_assessments
    }
    assessed_count = sum(1 for row in ai_system_rows if row.id in assessed_row_ids)

    risk_items = risk_analytics_service.summarize_rows(all_risk_rows, bands)
    in_review_count = sum(
        1 for record in [*policies, *procedures] if record.status == IN_REVIEW_STATUS
    )

    return DashboardSummary(
        policies=StatusCounts(
            total=len(policies), by_status=dict(Counter(p.status for p in policies))
        ),
        procedures=StatusCounts(
            total=len(procedures), by_status=dict(Counter(p.status for p in procedures))
        ),
        ai_systems=AISystemSummary(
            total=len(ai_system_rows), by_risk_tier=dict(risk_tier_counts)
        ),
        risk_assessments=RiskAssessmentSummary(
            total=len(risk_assessments),
            by_status=dict(Counter(ra.status for ra in risk_assessments)),
            high_risk_count=high_risk_count,
        ),
        risk_items=risk_items,
        coverage=CoverageSummary(
            ai_systems_total=len(ai_system_rows),
            ai_systems_assessed=assessed_count,
            policies_total=len(policies),
            policies_approved=sum(1 for p in policies if p.status == APPROVED_STATUS),
            procedures_total=len(procedures),
            procedures_approved=sum(1 for p in procedures if p.status == APPROVED_STATUS),
        ),
        attention=_attention(
            overdue_count=risk_items.overdue_count,
            unassessed_count=len(ai_system_rows) - assessed_count,
            in_review_count=in_review_count,
            high_risk_count=high_risk_count,
        ),
        matrix=risk_analytics_service.matrix_cells(all_risk_rows),
        criteria=risk_criteria_service.get_criteria(db),
    )
