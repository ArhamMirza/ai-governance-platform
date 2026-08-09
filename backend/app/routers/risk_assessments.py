from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.models.risk_assessment import RiskAssessment
from app.schemas.risk_assessment import (
    RiskAssessmentCreate,
    RiskAssessmentRead,
    RiskAssessmentUpdate,
)
from app.schemas.sheet import ColumnsUpdate, RowCreate, RowUpdate, SheetRowRead
from app.services import risk_assessment_service

router = APIRouter(prefix="/risk-assessments", tags=["risk-assessments"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _to_read(db: Session, risk_assessment: RiskAssessment) -> RiskAssessmentRead:
    overall_risk_rating = risk_assessment_service.compute_overall_risk_rating(
        db, risk_assessment.sheet_id
    )
    return RiskAssessmentRead(
        id=risk_assessment.id,
        ai_system_row_id=risk_assessment.ai_system_row_id,
        sheet_id=risk_assessment.sheet_id,
        framework_tags=risk_assessment.framework_tags,
        status=risk_assessment.status,
        assessor_id=risk_assessment.assessor_id,
        assessment_date=risk_assessment.assessment_date,
        overall_risk_rating=overall_risk_rating,
        created_at=risk_assessment.created_at,
        updated_at=risk_assessment.updated_at,
    )


@router.get("", response_model=list[RiskAssessmentRead])
def list_risk_assessments(db: Session = Depends(get_db)) -> list[RiskAssessmentRead]:
    return [_to_read(db, ra) for ra in risk_assessment_service.list_risk_assessments(db)]


@router.post("", response_model=RiskAssessmentRead, status_code=201)
def create_risk_assessment(
    data: RiskAssessmentCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> RiskAssessmentRead:
    risk_assessment = risk_assessment_service.create_risk_assessment(db, data, actor_id)
    return _to_read(db, risk_assessment)


@router.get("/{risk_assessment_id}", response_model=RiskAssessmentRead)
def get_risk_assessment(
    risk_assessment_id: int, db: Session = Depends(get_db)
) -> RiskAssessmentRead:
    risk_assessment = risk_assessment_service.get_risk_assessment(db, risk_assessment_id)
    return _to_read(db, risk_assessment)


@router.put("/{risk_assessment_id}", response_model=RiskAssessmentRead)
def update_risk_assessment(
    risk_assessment_id: int,
    data: RiskAssessmentUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> RiskAssessmentRead:
    risk_assessment = risk_assessment_service.update_risk_assessment(
        db, risk_assessment_id, data, actor_id
    )
    return _to_read(db, risk_assessment)


@router.delete("/{risk_assessment_id}", status_code=204)
def delete_risk_assessment(
    risk_assessment_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    risk_assessment_service.delete_risk_assessment(db, risk_assessment_id, actor_id)


@router.put("/{risk_assessment_id}/columns", response_model=RiskAssessmentRead)
def set_columns(
    risk_assessment_id: int, data: ColumnsUpdate, db: Session = Depends(get_db)
) -> RiskAssessmentRead:
    risk_assessment_service.set_columns(db, risk_assessment_id, data.columns)
    risk_assessment = risk_assessment_service.get_risk_assessment(db, risk_assessment_id)
    return _to_read(db, risk_assessment)


@router.post("/{risk_assessment_id}/rows", response_model=SheetRowRead, status_code=201)
def add_row(
    risk_assessment_id: int, data: RowCreate, db: Session = Depends(get_db)
) -> SheetRowRead:
    return risk_assessment_service.add_row(db, risk_assessment_id, data.data)


@router.put("/{risk_assessment_id}/rows/{row_id}", response_model=SheetRowRead)
def update_row(
    risk_assessment_id: int, row_id: int, data: RowUpdate, db: Session = Depends(get_db)
) -> SheetRowRead:
    return risk_assessment_service.update_row(db, risk_assessment_id, row_id, data.data)


@router.delete("/{risk_assessment_id}/rows/{row_id}", status_code=204)
def delete_row(risk_assessment_id: int, row_id: int, db: Session = Depends(get_db)) -> None:
    risk_assessment_service.delete_row(db, risk_assessment_id, row_id)


@router.post("/{risk_assessment_id}/upload", response_model=RiskAssessmentRead)
def upload(
    risk_assessment_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
) -> RiskAssessmentRead:
    risk_assessment_service.import_upload(db, risk_assessment_id, file)
    risk_assessment = risk_assessment_service.get_risk_assessment(db, risk_assessment_id)
    return _to_read(db, risk_assessment)


@router.get("/{risk_assessment_id}/export")
def export(risk_assessment_id: int, db: Session = Depends(get_db)) -> Response:
    content = risk_assessment_service.export_xlsx(db, risk_assessment_id)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="risk_assessment.xlsx"'},
    )
