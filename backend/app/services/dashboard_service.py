from collections import Counter

from sqlalchemy.orm import Session

from app.repositories import policy_repository, procedure_repository, risk_assessment_repository
from app.schemas.dashboard import (
    AISystemSummary,
    DashboardSummary,
    RiskAssessmentSummary,
    StatusCounts,
)
from app.services import ai_system_inventory_service, risk_assessment_service

HIGH_RISK_THRESHOLD = 15


def get_summary(db: Session) -> DashboardSummary:
    policies = policy_repository.list_all(db)
    procedures = procedure_repository.list_all(db)
    ai_system_rows = ai_system_inventory_service.list_rows(db)
    risk_assessments = risk_assessment_repository.list_all(db)

    risk_tier_counts = Counter(
        str(row.data["risk_tier"]) if row.data.get("risk_tier") else "unspecified"
        for row in ai_system_rows
    )

    high_risk_count = 0
    for risk_assessment in risk_assessments:
        rating = risk_assessment_service.compute_overall_risk_rating(
            db, risk_assessment.sheet_id
        )
        if rating is not None and rating >= HIGH_RISK_THRESHOLD:
            high_risk_count += 1

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
    )
