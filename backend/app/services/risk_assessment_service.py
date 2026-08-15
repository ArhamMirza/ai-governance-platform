from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.risk_assessment import RiskAssessment
from app.models.sheet import Sheet, SheetRow
from app.repositories import risk_assessment_repository, sheet_repository
from app.schemas.risk_assessment import RiskAssessmentCreate, RiskAssessmentUpdate
from app.schemas.sheet import ColumnDef
from app.services import ai_system_inventory_service, audit_service, sheet_service

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
    ColumnDef(key="control_owner", label="Control Owner"),
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
    scores = [
        row.data["inherent_risk_score"]
        for row in rows
        if isinstance(row.data.get("inherent_risk_score"), int | float)
    ]
    return max(scores) if scores else None


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
        framework_tags=data.framework_tags,
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
    audit_service.log(db, "RiskAssessment", risk_assessment_id, "deleted", actor_id)


def get_sheet(db: Session, risk_assessment_id: int) -> Sheet:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    return sheet_service.get_sheet(db, risk_assessment.sheet_id)


def list_rows(db: Session, risk_assessment_id: int) -> list[SheetRow]:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    return sheet_service.list_rows(db, risk_assessment.sheet_id)


def set_columns(db: Session, risk_assessment_id: int, columns: list[ColumnDef]) -> Sheet:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    return sheet_service.set_columns(db, risk_assessment.sheet_id, columns)


def add_row(db: Session, risk_assessment_id: int, data: dict) -> SheetRow:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    return sheet_service.add_row(db, risk_assessment.sheet_id, data)


def update_row(db: Session, risk_assessment_id: int, row_id: int, data: dict) -> SheetRow:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    return sheet_service.update_row(db, risk_assessment.sheet_id, row_id, data)


def delete_row(db: Session, risk_assessment_id: int, row_id: int) -> None:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    sheet_service.delete_row(db, risk_assessment.sheet_id, row_id)


def export_xlsx(db: Session, risk_assessment_id: int) -> bytes:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    return sheet_service.export_xlsx(db, risk_assessment.sheet_id)


def import_upload(db: Session, risk_assessment_id: int, file: UploadFile) -> Sheet:
    risk_assessment = _get_or_raise(db, risk_assessment_id)
    return sheet_service.import_upload(db, risk_assessment.sheet_id, file)
