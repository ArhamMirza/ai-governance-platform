from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.compliance_status import ComplianceStatusSummary, ControlComplianceStatus
from app.services import compliance_status_service

router = APIRouter(prefix="/compliance-status", tags=["compliance-status"])


@router.get("", response_model=list[ControlComplianceStatus])
def get_status(
    framework: str | None = None, db: Session = Depends(get_db)
) -> list[ControlComplianceStatus]:
    return compliance_status_service.get_status(db, framework)


@router.get("/summary", response_model=ComplianceStatusSummary)
def get_summary(db: Session = Depends(get_db)) -> ComplianceStatusSummary:
    return compliance_status_service.get_summary(db)
