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


def list_for_entity_type(db: Session, entity_type: str) -> list[AuditLogEntry]:
    """Every entry for an entity type, across ids. For trails recorded
    per-item under one type -- a dataset's review is logged against its row
    id, so a single sheet has no one id to look them up by."""
    return list(
        db.scalars(
            select(AuditLogEntry)
            .where(AuditLogEntry.entity_type == entity_type)
            .order_by(AuditLogEntry.timestamp)
        )
    )


def latest_entry_by_entity(
    db: Session, entity_type: str, entity_ids: list[int], actions: list[str]
) -> dict[int, AuditLogEntry]:
    """Latest matching log entry per entity_id, for these actions -- one
    query for many entities, so a caller checking "who last submitted this,
    and when" across a batch of candidate records doesn't do it one at a
    time (see sheet_repository.list_rows_for_sheets for the same
    batch-by-id shape)."""
    if not entity_ids:
        return {}
    query = (
        select(AuditLogEntry)
        .where(
            AuditLogEntry.entity_type == entity_type,
            AuditLogEntry.entity_id.in_(entity_ids),
            AuditLogEntry.action.in_(actions),
        )
        .order_by(AuditLogEntry.entity_id, AuditLogEntry.timestamp)
    )
    result: dict[int, AuditLogEntry] = {}
    for entry in db.scalars(query):
        result[entry.entity_id] = entry
    return result
