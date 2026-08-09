from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLogEntry


def list_for_entity(
    db: Session, entity_type: str, entity_id: int, actions: list[str] | None = None
) -> list[AuditLogEntry]:
    query = select(AuditLogEntry).where(
        AuditLogEntry.entity_type == entity_type, AuditLogEntry.entity_id == entity_id
    )
    if actions is not None:
        query = query.where(AuditLogEntry.action.in_(actions))
    return list(db.scalars(query.order_by(AuditLogEntry.timestamp)))
