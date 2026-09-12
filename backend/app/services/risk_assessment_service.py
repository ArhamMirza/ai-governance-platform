from collections import Counter
from datetime import UTC, datetime

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core import review_cadence, risk_scoring
from app.core.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.risk_assessment import RiskAssessment, RiskAssessmentStatus
from app.models.sheet import Sheet, SheetRow
from app.repositories import evidence_repository, risk_assessment_repository, sheet_repository
from app.schemas.risk_assessment import (
    RiskAssessmentCreate,
    RiskAssessmentStats,
    RiskAssessmentUpdate,
    RiskPortfolioSummary,
)
from app.schemas.sheet import ColumnDef
from app.services import (
    ai_system_inventory_service,
    ai_system_lifecycle_service,
    audit_service,
    evidence_service,
    framework_service,
    governance_role_service,
    impact_assessment_service,
    risk_analytics_service,
    risk_criteria_service,
    sheet_service,
)

RISK_ITEM_ENTITY_TYPE = "RiskItem"

ENTITY_TYPE = "RiskAssessment"

OWNER_APPROVAL_ENTITY_TYPE = "RiskAssessmentOwnerApproval"
CAIGO_APPROVAL_ENTITY_TYPE = "RiskAssessmentCaigoApproval"

_PRE_APPROVAL_STATUSES = {RiskAssessmentStatus.DRAFT, RiskAssessmentStatus.IN_PROGRESS}
_GATED_STATUSES = {
    RiskAssessmentStatus.PENDING_OWNER_APPROVAL,
    RiskAssessmentStatus.PENDING_CAIGO_APPROVAL,
    RiskAssessmentStatus.COMPLETED,
}

DEFAULT_COLUMNS = [
    ColumnDef(key="category", label="Category"),
    ColumnDef(key="description", label="Description"),
    ColumnDef(key="likelihood", label="Likelihood", data_type="number"),
    ColumnDef(key="impact", label="Impact", data_type="number"),
    ColumnDef(key="inherent_risk_score", label="Inherent Risk Score", data_type="number"),
    ColumnDef(key="mitigation", label="Mitigation"),
    ColumnDef(key="residual_likelihood", label="Residual Likelihood", data_type="number"),
    ColumnDef(key="residual_impact", label="Residual Impact", data_type="number"),
    ColumnDef(key="residual_risk_score", label="Residual Risk Score", data_type="number"),
    ColumnDef(key="risk_owner", label="Risk Owner"),
    ColumnDef(key="treatment_deadline", label="Treatment Deadline", data_type="date"),
    ColumnDef(key="status", label="Status"),
]


def _get_or_raise(db: Session, risk_assessment_id: int) -> RiskAssessment:
    risk_assessment = risk_assessment_repository.get(db, risk_assessment_id)
    if risk_assessment is None:
        raise NotFoundError("RiskAssessment", risk_assessment_id)
    return risk_assessment


def _validate_ai_system_row(db: Session, ai_system_row_id: int) -> None:
    inventory_sheet = ai_system_inventory_service.get_or_create_sheet(db)
    row = sheet_repository.get_row(db, ai_system_row_id)
    if row is None or row.sheet_id != inventory_sheet.id:
        raise NotFoundError("AISystemRow", ai_system_row_id)


def compute_overall_risk_rating(db: Session, sheet_id: int) -> float | None:
    rows = sheet_repository.list_rows(db, sheet_id)
    return risk_analytics_service.overall_rating(rows)


def get_portfolio_summary(db: Session) -> RiskPortfolioSummary:
    """Portfolio-wide roll-up for the risk assessments landing page."""
    risk_assessments = risk_assessment_repository.list_all(db)
    rows_by_sheet = sheet_repository.list_rows_for_sheets(
        db, [risk_assessment.sheet_id for risk_assessment in risk_assessments]
    )
    all_rows = [row for rows in rows_by_sheet.values() for row in rows]

    bands = risk_criteria_service.get_bands(db)

    stats: list[RiskAssessmentStats] = []
    high_risk_count = 0
    for risk_assessment in risk_assessments:
        rows = rows_by_sheet.get(risk_assessment.sheet_id, [])
        summary = risk_analytics_service.summarize_rows(rows, bands)
        rating = risk_analytics_service.overall_rating(rows)
        if rating is not None and risk_scoring.is_high_risk(rating, bands):
            high_risk_count += 1

        stats.append(
            RiskAssessmentStats(
                id=risk_assessment.id,
                ai_system_row_id=risk_assessment.ai_system_row_id,
                status=risk_assessment.status,
                overall_risk_rating=rating,
                item_count=summary.total,
                high_count=summary.by_severity[risk_scoring.SEVERITY_HIGH],
                medium_count=summary.by_severity[risk_scoring.SEVERITY_MEDIUM],
                low_count=summary.by_severity[risk_scoring.SEVERITY_LOW],
                overdue_count=summary.overdue_count,
            )
        )

    # Worst first: unrated assessments sort last.
    stats.sort(key=lambda s: (s.overall_risk_rating is None, -(s.overall_risk_rating or 0)))

    return RiskPortfolioSummary(
        total_assessments=len(risk_assessments),
        by_status=dict(Counter(ra.status for ra in risk_assessments)),
        high_risk_count=high_risk_count,
        risk_items=risk_analytics_service.summarize_rows(all_rows, bands),
        matrix=risk_analytics_service.matrix_cells(all_rows),
        assessments=stats,
        criteria=risk_criteria_service.get_criteria(db),
    )


def list_risk_assessments(db: Session) -> list[RiskAssessment]:
    return risk_assessment_repository.list_all(db)


def get_for_ai_system(db: Session, ai_system_row_id: int) -> RiskAssessment | None:
    """An AI system has at most one risk assessment; its risk items live as
    rows on that assessment's sheet."""
    return next(
        (
            risk_assessment
            for risk_assessment in risk_assessment_repository.list_all(db)
            if risk_assessment.ai_system_row_id == ai_system_row_id
        ),
        None,
    )


def get_risk_assessment(db: Session, risk_assessment_id: int) -> RiskAssessment:
    return _get_or_raise(db, risk_assessment_id)


def create_risk_assessment(
    db: Session, data: RiskAssessmentCreate, actor_id: int | None
) -> RiskAssessment:
    _validate_ai_system_row(db, data.ai_system_row_id)

    # ISO 42001 sequences impact assessment before risk assessment: you can't
    # size a system's risks before establishing who it affects and how.
    if not impact_assessment_service.has_completed_for_ai_system(db, data.ai_system_row_id):
        raise ValidationError(
            "Complete an impact assessment for this AI system before opening a "
            "risk assessment against it."
        )

    # One per AI system -- further risks go in this assessment's sheet as new
    # rows, rather than spawning a parallel assessment.
    if get_for_ai_system(db, data.ai_system_row_id) is not None:
        raise ConflictError(
            "This AI system already has a risk assessment. Add risk items to it "
            "instead of creating another."
        )

    sheet = sheet_service.create_sheet(db, ENTITY_TYPE, "Risk Items", DEFAULT_COLUMNS)
    risk_assessment = RiskAssessment(
        ai_system_row_id=data.ai_system_row_id,
        sheet_id=sheet.id,
        assessor_id=data.assessor_id,
        assessment_date=data.assessment_date,
    )
    risk_assessment = risk_assessment_repository.create(db, risk_assessment)
    audit_service.log(
        db,
        "RiskAssessment",
        risk_assessment.id,
        "created",
        actor_id,
        {"ai_system_row_id": data.ai_system_row_id},
    )
    return risk_assessment


def update_risk_assessment(
    db: Session, risk_assessment_id: int, data: RiskAssessmentUpdate, actor_id: int | None
) -> RiskAssessment:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    changes = data.model_dump(exclude_unset=True)
    if "status" in changes and (
        changes["status"] in _GATED_STATUSES
        or risk_assessment.status not in _PRE_APPROVAL_STATUSES
    ):
        raise ValidationError(
            "Use the submit/approve endpoints to move a risk assessment through "
            "owner and CAIGO approval -- status can't be set directly once it's "
            "in the approval pipeline."
        )
    for field, value in changes.items():
        setattr(risk_assessment, field, value)

    risk_assessment = risk_assessment_repository.save(db, risk_assessment)
    audit_service.log(db, "RiskAssessment", risk_assessment.id, "updated", actor_id, changes)
    return risk_assessment


def _stamp_completed(risk_assessment: RiskAssessment) -> None:
    """Same cadence rule as ImpactAssessment -- completing stamps the date
    and schedules the next review so the two stay on one clock."""
    if risk_assessment.assessment_date is None:
        risk_assessment.assessment_date = datetime.now(UTC).date()
    risk_assessment.next_review_date = review_cadence.next_review_date(
        risk_assessment.assessment_date
    )


def submit_for_owner_approval(
    db: Session, risk_assessment_id: int, actor_id: int | None
) -> RiskAssessment:
    """Implementation Team submits their work. If the AI system's owner is
    the one submitting, they can't meaningfully approve their own work, so
    this skips straight to the CAIGO stage instead of waiting on them."""
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    if risk_assessment.status not in _PRE_APPROVAL_STATUSES:
        raise ConflictError(
            f"RiskAssessment {risk_assessment_id} must be draft or in_progress to "
            f"submit for approval, currently '{risk_assessment.status}'"
        )

    lifecycle = ai_system_lifecycle_service.get_or_create(
        db, risk_assessment.ai_system_row_id
    )
    owner_id = lifecycle.owner_id
    if owner_id is None:
        raise ValidationError(
            "This AI system has no owner assigned yet -- assign an AI System "
            "Owner before submitting for approval, or the owner stage can "
            "never be approved."
        )

    audit_service.log(
        db, OWNER_APPROVAL_ENTITY_TYPE, risk_assessment_id, "submitted_for_review", actor_id
    )
    if owner_id is not None and actor_id == owner_id:
        risk_assessment.status = RiskAssessmentStatus.PENDING_CAIGO_APPROVAL
        audit_service.log(
            db, CAIGO_APPROVAL_ENTITY_TYPE, risk_assessment_id, "submitted_for_review", actor_id
        )
    else:
        risk_assessment.status = RiskAssessmentStatus.PENDING_OWNER_APPROVAL

    risk_assessment = risk_assessment_repository.save(db, risk_assessment)
    audit_service.log(db, ENTITY_TYPE, risk_assessment_id, "submitted_for_review", actor_id)
    return risk_assessment


def approve_owner_stage(
    db: Session, risk_assessment_id: int, actor_id: int | None
) -> RiskAssessment:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    if risk_assessment.status != RiskAssessmentStatus.PENDING_OWNER_APPROVAL:
        raise ConflictError(
            f"RiskAssessment {risk_assessment_id} must be pending owner approval, "
            f"currently '{risk_assessment.status}'"
        )

    lifecycle = ai_system_lifecycle_service.get_or_create(
        db, risk_assessment.ai_system_row_id
    )
    if actor_id is not None and actor_id != lifecycle.owner_id:
        raise AuthorizationError(
            "Only this AI system's owner can approve this stage."
        )
    audit_service.require_different_approver(
        db, OWNER_APPROVAL_ENTITY_TYPE, risk_assessment_id, actor_id
    )

    risk_assessment.owner_approved_by = actor_id
    risk_assessment.owner_approved_at = datetime.now(UTC)
    risk_assessment.status = RiskAssessmentStatus.PENDING_CAIGO_APPROVAL
    risk_assessment = risk_assessment_repository.save(db, risk_assessment)
    audit_service.log(
        db, OWNER_APPROVAL_ENTITY_TYPE, risk_assessment_id, "approved", actor_id
    )
    audit_service.log(
        db, CAIGO_APPROVAL_ENTITY_TYPE, risk_assessment_id, "submitted_for_review", actor_id
    )
    return risk_assessment


def approve_caigo_stage(
    db: Session, risk_assessment_id: int, actor_id: int | None
) -> RiskAssessment:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    if risk_assessment.status != RiskAssessmentStatus.PENDING_CAIGO_APPROVAL:
        raise ConflictError(
            f"RiskAssessment {risk_assessment_id} must be pending CAIGO approval, "
            f"currently '{risk_assessment.status}'"
        )

    governance_role_service.require_caigo(db, actor_id)
    audit_service.require_different_approver(
        db, CAIGO_APPROVAL_ENTITY_TYPE, risk_assessment_id, actor_id
    )

    risk_assessment.caigo_approved_by = actor_id
    risk_assessment.caigo_approved_at = datetime.now(UTC)
    risk_assessment.status = RiskAssessmentStatus.COMPLETED
    _stamp_completed(risk_assessment)
    risk_assessment = risk_assessment_repository.save(db, risk_assessment)
    audit_service.log(
        db, CAIGO_APPROVAL_ENTITY_TYPE, risk_assessment_id, "approved", actor_id
    )
    return risk_assessment


def delete_risk_assessment(db: Session, risk_assessment_id: int, actor_id: int | None) -> None:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    sheet = sheet_repository.get(db, risk_assessment.sheet_id)
    if sheet is not None:
        for row in sheet_repository.list_rows(db, sheet.id):
            evidence_service.delete_all_for_entity(db, RISK_ITEM_ENTITY_TYPE, row.id)
    risk_assessment_repository.delete(db, risk_assessment)
    if sheet is not None:
        sheet_repository.delete_all_rows(db, sheet.id)
        sheet_repository.delete(db, sheet)
    framework_service.delete_tags(db, "RiskAssessment", risk_assessment_id)
    audit_service.log(db, "RiskAssessment", risk_assessment_id, "deleted", actor_id)


def get_sheet(db: Session, risk_assessment_id: int) -> Sheet:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    return sheet_service.get_sheet(db, risk_assessment.sheet_id)


def list_rows(db: Session, risk_assessment_id: int) -> list[SheetRow]:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    return sheet_service.list_rows(db, risk_assessment.sheet_id)


def set_columns(
    db: Session, risk_assessment_id: int, columns: list[ColumnDef], actor_id: int | None
) -> Sheet:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    result = sheet_service.set_columns(db, risk_assessment.sheet_id, columns)
    audit_service.log(db, ENTITY_TYPE, risk_assessment_id, "columns_updated", actor_id)
    return result


def add_row(db: Session, risk_assessment_id: int, data: dict, actor_id: int | None) -> SheetRow:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    row = sheet_service.add_row(db, risk_assessment.sheet_id, data)
    audit_service.log(
        db, ENTITY_TYPE, risk_assessment_id, "row_added", actor_id, {"row_id": row.id}
    )
    return row


def update_row(
    db: Session, risk_assessment_id: int, row_id: int, data: dict, actor_id: int | None
) -> SheetRow:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    row = sheet_service.update_row(db, risk_assessment.sheet_id, row_id, data)
    audit_service.log(
        db, ENTITY_TYPE, risk_assessment_id, "row_updated", actor_id, {"row_id": row_id}
    )
    return row


def delete_row(
    db: Session, risk_assessment_id: int, row_id: int, actor_id: int | None
) -> None:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    evidence_service.delete_all_for_entity(db, RISK_ITEM_ENTITY_TYPE, row_id)
    sheet_service.delete_row(db, risk_assessment.sheet_id, row_id)
    audit_service.log(
        db, ENTITY_TYPE, risk_assessment_id, "row_deleted", actor_id, {"row_id": row_id}
    )


def close_risk_item(
    db: Session, risk_assessment_id: int, row_id: int, actor_id: int | None
) -> SheetRow:
    """Marks a risk item treated. Requires at least one piece of evidence
    already attached (see evidence entity_type=RiskItem) -- a risk can't be
    closed on say-so alone."""
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    row = sheet_repository.get_row(db, row_id)
    if row is None or row.sheet_id != risk_assessment.sheet_id:
        raise NotFoundError("SheetRow", row_id)

    if risk_scoring.is_treated(row.data.get("status")):
        raise ConflictError(f"Risk item {row_id} is already closed.")

    if not evidence_repository.list_at_level(db, RISK_ITEM_ENTITY_TYPE, row_id, None):
        raise ValidationError(
            "Attach at least one piece of evidence before closing this risk item."
        )

    row.data = {
        **row.data,
        "status": "closed",
        "closed_at": datetime.now(UTC).isoformat(),
        "closed_by": actor_id,
    }
    row = sheet_repository.save_row(db, row)
    audit_service.log(
        db, ENTITY_TYPE, risk_assessment_id, "risk_item_closed", actor_id, {"row_id": row_id}
    )
    return row


def export_xlsx(db: Session, risk_assessment_id: int) -> bytes:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    return sheet_service.export_xlsx(db, risk_assessment.sheet_id)


def import_upload(
    db: Session, risk_assessment_id: int, file: UploadFile, actor_id: int | None
) -> Sheet:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    result = sheet_service.import_upload(db, risk_assessment.sheet_id, file)
    audit_service.log(db, ENTITY_TYPE, risk_assessment_id, "sheet_uploaded", actor_id)
    return result
