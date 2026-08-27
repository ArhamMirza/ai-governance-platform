from collections import Counter

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core import risk_scoring
from app.core.exceptions import NotFoundError
from app.models.risk_assessment import RiskAssessment
from app.models.sheet import Sheet, SheetRow
from app.repositories import risk_assessment_repository, sheet_repository
from app.schemas.risk_assessment import (
    RiskAssessmentCreate,
    RiskAssessmentStats,
    RiskAssessmentUpdate,
    RiskPortfolioSummary,
)
from app.schemas.sheet import ColumnDef
from app.services import (
    ai_system_inventory_service,
    audit_service,
    framework_service,
    risk_analytics_service,
    risk_criteria_service,
    sheet_service,
)

ENTITY_TYPE = "RiskAssessment"

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


def get_risk_assessment(db: Session, risk_assessment_id: int) -> RiskAssessment:
    return _get_or_raise(db, risk_assessment_id)


def create_risk_assessment(
    db: Session, data: RiskAssessmentCreate, actor_id: int | None
) -> RiskAssessment:
    _validate_ai_system_row(db, data.ai_system_row_id)

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
    for field, value in changes.items():
        setattr(risk_assessment, field, value)
    risk_assessment = risk_assessment_repository.save(db, risk_assessment)
    audit_service.log(db, "RiskAssessment", risk_assessment.id, "updated", actor_id, changes)
    return risk_assessment


def delete_risk_assessment(db: Session, risk_assessment_id: int, actor_id: int | None) -> None:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    sheet = sheet_repository.get(db, risk_assessment.sheet_id)
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
    sheet_service.delete_row(db, risk_assessment.sheet_id, row_id)
    audit_service.log(
        db, ENTITY_TYPE, risk_assessment_id, "row_deleted", actor_id, {"row_id": row_id}
    )


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
