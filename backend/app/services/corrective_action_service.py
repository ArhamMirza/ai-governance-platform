"""Nonconformity and corrective action tracking -- ISO/IEC 42001 Clause
10.1/10.2.

A flat, independent record like Policy/Procedure: create it, work it
(open -> in_progress), submit the finished fix for someone else to verify
(pending_verification), and have that person -- the Chief AI Governance
Officer, never the assignee themselves -- close it out. The same
segregation-of-duties pairing (require_caigo + require_different_approver)
Policy/Procedure approval already uses, so the frontend's existing
useCanApprove hook needs no changes to work here too.

Overdue is computed, never stored (see is_overdue below), matching
risk_scoring.is_overdue / review_cadence.is_review_overdue -- it can't
silently disagree with what a record's own fields say.
"""

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core.concurrency import claim_transition
from app.core.exceptions import InvalidStatusTransitionError, NotFoundError, ValidationError
from app.models.corrective_action import CorrectiveAction, CorrectiveActionStatus
from app.repositories import corrective_action_repository, evidence_repository
from app.schemas.corrective_action import CorrectiveActionCreate, CorrectiveActionUpdate
from app.services import audit_service, framework_service, governance_role_service

ENTITY_TYPE = "CorrectiveAction"
SUBMITTED_FOR_VERIFICATION = "submitted_for_verification"

# Editable directly through update_corrective_action; reaching
# pending_verification or closed needs the dedicated endpoints below, which
# is where the evidence and CAIGO gates live.
_EDITABLE_STATUSES = {CorrectiveActionStatus.OPEN, CorrectiveActionStatus.IN_PROGRESS}
_DIRECTLY_SETTABLE_STATUSES = {CorrectiveActionStatus.OPEN, CorrectiveActionStatus.IN_PROGRESS}


def is_overdue(due_date: date, status: str, today: date | None = None) -> bool:
    """A corrective action is overdue once its due date has passed and it
    isn't closed -- closed is closed regardless of when it happened."""
    reference = today if today is not None else datetime.now(UTC).date()
    return status != CorrectiveActionStatus.CLOSED and due_date < reference


def _get_or_raise(db: Session, corrective_action_id: int) -> CorrectiveAction:
    corrective_action = corrective_action_repository.get(db, corrective_action_id)
    if corrective_action is None:
        raise NotFoundError("CorrectiveAction", corrective_action_id)
    return corrective_action


def _claim(db: Session, corrective_action: CorrectiveAction, expected: str, changes: dict) -> None:
    if not claim_transition(db, corrective_action, expected_statuses=expected, changes=changes):
        raise InvalidStatusTransitionError(
            f"CorrectiveAction {corrective_action.id} is no longer '{expected}' -- someone "
            f"else has already moved it on, and it is now '{corrective_action.status}'."
        )


def list_corrective_actions(db: Session) -> list[CorrectiveAction]:
    return corrective_action_repository.list_all(db)


def get_corrective_action(db: Session, corrective_action_id: int) -> CorrectiveAction:
    return _get_or_raise(db, corrective_action_id)


def create_corrective_action(
    db: Session, data: CorrectiveActionCreate, actor_id: int | None
) -> CorrectiveAction:
    corrective_action = CorrectiveAction(
        title=data.title,
        nonconformity_description=data.nonconformity_description,
        root_cause=data.root_cause,
        action_description=data.action_description,
        source_type=data.source_type,
        source_id=data.source_id,
        assignee_id=data.assignee_id,
        due_date=data.due_date,
        status=CorrectiveActionStatus.OPEN,
    )
    corrective_action = corrective_action_repository.create(db, corrective_action)
    audit_service.log(
        db,
        ENTITY_TYPE,
        corrective_action.id,
        "created",
        actor_id,
        {"title": corrective_action.title},
    )
    return corrective_action


def update_corrective_action(
    db: Session, corrective_action_id: int, data: CorrectiveActionUpdate, actor_id: int | None
) -> CorrectiveAction:
    corrective_action = _get_or_raise(db, corrective_action_id)
    if corrective_action.status not in _EDITABLE_STATUSES:
        raise InvalidStatusTransitionError(
            f"CorrectiveAction {corrective_action_id} cannot be edited while status is "
            f"'{corrective_action.status}'; reopen it first."
        )

    changes = data.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] not in _DIRECTLY_SETTABLE_STATUSES:
        raise InvalidStatusTransitionError(
            "status may only be set to 'open' or 'in_progress' here; use "
            "submit-for-verification/verify-and-close to move it further."
        )
    for field, value in changes.items():
        setattr(corrective_action, field, value)

    corrective_action = corrective_action_repository.save(db, corrective_action)
    audit_service.log(db, ENTITY_TYPE, corrective_action.id, "updated", actor_id, changes)
    return corrective_action


def submit_for_verification(
    db: Session, corrective_action_id: int, actor_id: int | None
) -> CorrectiveAction:
    """Moves a corrective action from in_progress to pending_verification.
    Requires the fix to actually be described, and at least one piece of
    evidence attached -- the same "not on say-so alone" rule
    risk_assessment_service.close_risk_item applies to closing a risk item."""
    corrective_action = _get_or_raise(db, corrective_action_id)
    if corrective_action.status != CorrectiveActionStatus.IN_PROGRESS:
        raise InvalidStatusTransitionError(
            f"CorrectiveAction {corrective_action_id} must be in 'in_progress' status to "
            f"submit for verification, currently '{corrective_action.status}'"
        )
    if not (corrective_action.action_description or "").strip():
        raise ValidationError(
            "Describe the corrective action taken before submitting it for verification."
        )
    if not evidence_repository.list_at_level(db, ENTITY_TYPE, corrective_action_id, None):
        raise ValidationError(
            "Attach at least one piece of evidence before submitting this corrective "
            "action for verification."
        )

    _claim(
        db,
        corrective_action,
        CorrectiveActionStatus.IN_PROGRESS,
        {"status": CorrectiveActionStatus.PENDING_VERIFICATION},
    )
    audit_service.log(db, ENTITY_TYPE, corrective_action.id, SUBMITTED_FOR_VERIFICATION, actor_id)
    return corrective_action


def verify_and_close(
    db: Session, corrective_action_id: int, actor_id: int | None
) -> CorrectiveAction:
    """Only the Chief AI Governance Officer can verify a fix, and never the
    same person who submitted it for verification -- the identical pairing
    Policy/Procedure approval uses, so a corrective action can't be closed
    by whoever did the work."""
    corrective_action = _get_or_raise(db, corrective_action_id)
    if corrective_action.status != CorrectiveActionStatus.PENDING_VERIFICATION:
        raise InvalidStatusTransitionError(
            f"CorrectiveAction {corrective_action_id} must be in 'pending_verification' "
            f"status to verify and close, currently '{corrective_action.status}'"
        )
    governance_role_service.require_caigo(db, actor_id)
    audit_service.require_different_approver(
        db,
        ENTITY_TYPE,
        corrective_action_id,
        actor_id,
        submitted_actions=(SUBMITTED_FOR_VERIFICATION,),
    )

    now = datetime.now(UTC)
    _claim(
        db,
        corrective_action,
        CorrectiveActionStatus.PENDING_VERIFICATION,
        {
            "status": CorrectiveActionStatus.CLOSED,
            "closed_by": actor_id,
            "closed_at": now,
        },
    )
    audit_service.log(db, ENTITY_TYPE, corrective_action.id, "verified_and_closed", actor_id)
    return corrective_action


def reopen(db: Session, corrective_action_id: int, actor_id: int | None) -> CorrectiveAction:
    """Reopens a closed corrective action -- e.g. the fix later turns out not
    to have held. Moves back to in_progress, clearing the closure fields, so
    it must be verified and closed again through the same gates."""
    corrective_action = _get_or_raise(db, corrective_action_id)
    if corrective_action.status != CorrectiveActionStatus.CLOSED:
        raise InvalidStatusTransitionError(
            f"CorrectiveAction {corrective_action_id} must be 'closed' to reopen, "
            f"currently '{corrective_action.status}'"
        )
    _claim(
        db,
        corrective_action,
        CorrectiveActionStatus.CLOSED,
        {
            "status": CorrectiveActionStatus.IN_PROGRESS,
            "closed_by": None,
            "closed_at": None,
        },
    )
    audit_service.log(db, ENTITY_TYPE, corrective_action.id, "reopened", actor_id)
    return corrective_action


def reopen_if_evidence_gone(db: Session, corrective_action_id: int, actor_id: int | None) -> None:
    """Reopens a closed corrective action whose last piece of evidence has
    just been deleted -- submit_for_verification won't move one forward
    without proof, so a closure must not outlive it either. Mirrors
    risk_assessment_service.reopen_if_evidence_gone."""
    corrective_action = corrective_action_repository.get(db, corrective_action_id)
    if corrective_action is None or corrective_action.status != CorrectiveActionStatus.CLOSED:
        return
    if evidence_repository.list_at_level(db, ENTITY_TYPE, corrective_action_id, None):
        return
    reopen(db, corrective_action_id, actor_id)


def delete_corrective_action(db: Session, corrective_action_id: int, actor_id: int | None) -> None:
    # Imported here rather than at module scope, matching policy_service's
    # own reasoning: evidence_service would otherwise import this module
    # back, which is circular.
    from app.services import evidence_service

    corrective_action = _get_or_raise(db, corrective_action_id)
    if corrective_action.status != CorrectiveActionStatus.OPEN:
        raise InvalidStatusTransitionError(
            f"CorrectiveAction {corrective_action_id} cannot be deleted while status is "
            f"'{corrective_action.status}'; only a still-open corrective action can be deleted"
        )
    corrective_action_repository.delete(db, corrective_action)
    evidence_service.delete_all_for_entity(db, ENTITY_TYPE, corrective_action_id)
    framework_service.delete_tags(db, ENTITY_TYPE, corrective_action_id)
    audit_service.log(db, ENTITY_TYPE, corrective_action_id, "deleted", actor_id)
