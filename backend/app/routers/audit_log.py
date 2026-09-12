from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import audit_log_repository
from app.schemas.audit_log import AuditLogEntryRead

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("", response_model=list[AuditLogEntryRead])
def list_audit_log(
    entity_type: str, entity_id: int | None = None, db: Session = Depends(get_db)
) -> list[AuditLogEntryRead]:
    """Omitting entity_id returns the whole trail for that entity type. Needed
    where a trail is recorded per item under one type -- a dataset's review is
    logged against its row id, so the sheet has no single id to ask for."""
    if entity_id is None:
        return audit_log_repository.list_for_entity_type(db, entity_type)
    return audit_log_repository.list_for_entity(db, entity_type, entity_id)
