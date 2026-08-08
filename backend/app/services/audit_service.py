from sqlalchemy.orm import Session

from app.models.audit_log import AuditLogEntry


def log(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    actor_id: int | None,
    diff: dict | None = None,
) -> AuditLogEntry:
    entry = AuditLogEntry(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_id=actor_id,
        diff=diff,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
