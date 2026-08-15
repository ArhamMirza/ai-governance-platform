from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import audit_log_repository
from app.schemas.audit_log import AuditLogEntryRead

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("", response_model=list[AuditLogEntryRead])
def list_audit_log(
    entity_type: str, entity_id: int, db: Session = Depends(get_db)
) -> list[AuditLogEntryRead]:
    return audit_log_repository.list_for_entity(db, entity_type, entity_id)
