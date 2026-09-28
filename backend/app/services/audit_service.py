from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.audit_log import AuditLogEntry
from app.repositories import audit_log_repository


def require_different_approver(
    db: Session,
    entity_type: str,
    entity_id: int,
    approver_id: int | None,
    submitted_actions: tuple[str, ...] = ("submitted_for_review",),
) -> None:
    """Segregation of duties: whoever most recently submitted this entity
    for review cannot be the one who approves it, regardless of role -- an
    admin can't rubber-stamp their own submission either. Looks at the
    latest matching audit entry rather than a stored column, since the audit
    log is already the durable record of who did what.

    ``submitted_actions`` defaults to the review-submission vocabulary every
    existing caller uses; a workflow with its own submission action name
    (e.g. corrective_action_service's "submitted_for_verification") passes
    its own action here instead of overloading "submitted_for_review"."""
    if approver_id is None:
        # No real actor to compare against (e.g. the seed script, or a
        # direct service call outside of HTTP) -- nothing to enforce.
        return

    submissions = audit_log_repository.list_for_entity(
        db, entity_type, entity_id, list(submitted_actions)
    )
    if submissions and submissions[-1].actor_id == approver_id:
        raise ConflictError(
            f"{entity_type} {entity_id} was submitted for review by this same user; "
            "a different user must approve it."
        )


def log(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    actor_id: int | None,
    diff: dict | None = None,
) -> AuditLogEntry:
    # The diff column is plain JSON, and callers routinely pass a schema's
    # model_dump() straight through -- dates, datetimes and enums included.
    # Encoding here, once, keeps every caller from having to remember to.
    entry = AuditLogEntry(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_id=actor_id,
        diff=jsonable_encoder(diff) if diff is not None else None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
