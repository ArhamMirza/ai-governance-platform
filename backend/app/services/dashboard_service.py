from collections import Counter
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core import review_cadence, risk_scoring
from app.models.impact_assessment import ImpactAssessmentStatus
from app.models.risk_assessment import RiskAssessment
from app.models.sheet import SheetRow
from app.repositories import (
    impact_assessment_repository,
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
    MyRiskItem,
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
    no_impact_assessment_count: int,
    review_overdue_count: int,
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
            key="no_impact_assessment",
            label="AI systems without a completed impact assessment",
            count=no_impact_assessment_count,
            severity="danger",
        ),
        AttentionItem(
            key="assessments_review_overdue",
            label="Assessments overdue for annual review",
            count=review_overdue_count,
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


def _my_risk_items(
    risk_assessments: list[RiskAssessment],
    rows_by_sheet: dict[int, list[SheetRow]],
    actor_id: int,
) -> list[MyRiskItem]:
    """Open risk items whose risk_owner cell matches the requesting user.
    risk_owner is stored as a stringified user id (see the DataGrid owner
    picker on RiskAssessment sheets) -- unassigned or legacy free-text
    owners (pre-dating real user accounts) simply never match."""
    owner_key = str(actor_id)
    items: list[MyRiskItem] = []
    for risk_assessment in risk_assessments:
        for row in rows_by_sheet.get(risk_assessment.sheet_id, []):
            if str(row.data.get("risk_owner", "")) != owner_key:
                continue
            if risk_scoring.is_treated(row.data.get("status")):
                continue
            items.append(
                MyRiskItem(
                    risk_assessment_id=risk_assessment.id,
                    row_id=row.id,
                    category=row.data.get("category"),
                    description=row.data.get("description"),
                    status=row.data.get("status"),
                    treatment_deadline=row.data.get("treatment_deadline"),
                    overdue=risk_scoring.is_overdue(row.data),
                )
            )
    # Overdue first, otherwise oldest deadline first (None sorts last).
    items.sort(key=lambda item: (not item.overdue, item.treatment_deadline or "9999-99-99"))
    return items


def get_summary(db: Session, actor_id: int) -> DashboardSummary:
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

    # Impact assessment coverage: an AI system counts once it has at least one
    # COMPLETED impact assessment (drafts don't satisfy clause 8.4).
    impact_assessments = impact_assessment_repository.list_all(db)
    impact_assessed_row_ids = {
        assessment.ai_system_row_id
        for assessment in impact_assessments
        if assessment.status == ImpactAssessmentStatus.COMPLETED
    }
    impact_assessed_count = sum(
        1 for row in ai_system_rows if row.id in impact_assessed_row_ids
    )

    today = datetime.now(UTC).date()
    review_overdue_count = sum(
        1
        for assessment in [*impact_assessments, *risk_assessments]
        if review_cadence.is_review_overdue(assessment.next_review_date, today)
    )

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
            ai_systems_impact_assessed=impact_assessed_count,
            assessments_review_overdue=review_overdue_count,
            policies_total=len(policies),
            policies_approved=sum(1 for p in policies if p.status == APPROVED_STATUS),
            procedures_total=len(procedures),
            procedures_approved=sum(1 for p in procedures if p.status == APPROVED_STATUS),
        ),
        attention=_attention(
            overdue_count=risk_items.overdue_count,
            unassessed_count=len(ai_system_rows) - assessed_count,
            no_impact_assessment_count=len(ai_system_rows) - impact_assessed_count,
            review_overdue_count=review_overdue_count,
            in_review_count=in_review_count,
            high_risk_count=high_risk_count,
        ),
        matrix=risk_analytics_service.matrix_cells(all_risk_rows),
        criteria=risk_criteria_service.get_criteria(db),
        my_risk_items=_my_risk_items(risk_assessments, rows_by_sheet, actor_id),
    )
