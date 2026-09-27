"""The two-stage approval chain (this AI system's Owner, then the Chief AI
Governance Officer) that risk_assessment_service and impact_assessment_service
both run against their own model. Extracted here so the chain's actual rules
-- an AI system with no owner assigned can't be submitted; the owner
auto-skips straight to the CAIGO stage if they're also the one submitting;
no one approves their own submission -- live in one place instead of being
kept in lockstep by hand across two near-identical services.

Each caller passes in its own model instance, status values, and audit
entity-type strings; this module writes the instance's approval fields and
raises the same exceptions either service already raised. The caller still
owns fetching the record and logging its own entity-type
"submitted_for_review" audit entry, exactly as it did before this was
extracted -- only the shared approval logic moved.

Every transition here is written with the status it was checked against
restated in the WHERE clause (see concurrency.claim_transition), because
each of those checks runs in a transaction of its own: two approvers can
both find a record pending and both pass every gate, and without the guard
the record would simply record whichever of them committed last."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.core import review_cadence
from app.core.concurrency import claim_transition, withdraw_transition
from app.core.exceptions import AuthorizationError, ConflictError, ValidationError
from app.services import ai_system_lifecycle_service, audit_service, governance_role_service


class ApprovableAssessment(Protocol):
    id: int
    ai_system_row_id: int
    status: Any
    assessment_date: Any
    next_review_date: Any
    owner_approved_by: int | None
    owner_approved_at: datetime | None
    caigo_approved_by: int | None
    caigo_approved_at: datetime | None


def completion_dates(assessment: ApprovableAssessment) -> dict[str, Any]:
    """Completing an assessment stamps when it happened and when it's next
    due, so the review cadence can't be left unset by accident."""
    assessment_date = assessment.assessment_date or datetime.now(UTC).date()
    return {
        "assessment_date": assessment_date,
        "next_review_date": review_cadence.next_review_date(assessment_date),
    }


def _refuse(assessment: ApprovableAssessment, entity_label: str, expected: str) -> None:
    raise ConflictError(
        f"{entity_label} {assessment.id} is no longer {expected} -- someone else "
        f"has already moved it on, and it is now '{assessment.status}'."
    )


def revert_to_draft(
    db: Session,
    assessment: ApprovableAssessment,
    actor_id: int | None,
    *,
    draft_status: Any,
    caigo_approval_entity_type: str,
) -> bool:
    """An approval describes the assessment as it stood when it was signed
    off, so changing what was assessed withdraws it: the record goes back to
    draft and has to be re-submitted. Progress *against* an assessment --
    treating and closing risk items -- is not a change to it, and the callers
    decide which is which.

    Returns whether anything was withdrawn. Mirrors
    data_inventory_service._revert_review, which applies the same rule to a
    dataset entry; the two are separate only because a DataInventoryRecord has
    no owner-approval stage to clear."""
    if assessment.status == draft_status:
        return False

    # Unguarded, and writing every field rather than assigning them: an
    # approval landing between the read above and this write still has to be
    # taken down, because it describes content that has since changed. See
    # concurrency.withdraw_transition.
    withdraw_transition(
        db,
        assessment,
        {
            "status": draft_status,
            "owner_approved_by": None,
            "owner_approved_at": None,
            "caigo_approved_by": None,
            "caigo_approved_at": None,
        },
    )
    audit_service.log(
        db, caigo_approval_entity_type, assessment.id, "review_reset_by_edit", actor_id
    )
    return True


def submit_for_owner_approval(
    db: Session,
    assessment: ApprovableAssessment,
    actor_id: int | None,
    *,
    entity_label: str,
    owner_approval_entity_type: str,
    caigo_approval_entity_type: str,
    pre_approval_statuses: set,
    pre_approval_label: str,
    pending_owner_status: Any,
    pending_caigo_status: Any,
    require_ready: Callable[[], None] | None = None,
) -> None:
    """Implementation Team submits their work. If the AI system's owner is
    the one submitting, they can't meaningfully approve their own work, so
    this skips straight to the CAIGO stage instead of waiting on them.

    require_ready is the caller's own rule for whether the record has enough
    in it to be signed off at all -- run after the status check, so a record
    that's already moved on is refused as a conflict rather than as
    incomplete."""
    if assessment.status not in pre_approval_statuses:
        raise ConflictError(
            f"{entity_label} {assessment.id} must be {pre_approval_label} to "
            f"submit for approval, currently '{assessment.status}'"
        )
    if require_ready is not None:
        require_ready()

    lifecycle = ai_system_lifecycle_service.get_or_create(db, assessment.ai_system_row_id)
    owner_id = lifecycle.owner_id
    if owner_id is None:
        raise ValidationError(
            "This AI system has no owner assigned yet -- assign an AI System "
            "Owner before submitting for approval, or the owner stage can "
            "never be approved."
        )

    owner_is_submitting = actor_id == owner_id
    if owner_is_submitting:
        # The owner stage is about to be skipped entirely, so this
        # submission also lands as the CAIGO stage's own "submitted_for_review"
        # below -- if the submitter is the only person who could ever approve
        # that stage, refuse now rather than leave the record stuck there.
        governance_role_service.require_a_possible_approver(db, actor_id)
    next_status = pending_caigo_status if owner_is_submitting else pending_owner_status
    if not claim_transition(
        db,
        assessment,
        expected_statuses=pre_approval_statuses,
        changes={"status": next_status},
    ):
        _refuse(assessment, entity_label, pre_approval_label)

    # Logged only once the submission has actually landed. Two simultaneous
    # submissions would otherwise write two "submitted_for_review" entries,
    # and require_different_approver reads only the latest -- so the earlier
    # submitter could go on to approve their own work.
    audit_service.log(
        db, owner_approval_entity_type, assessment.id, "submitted_for_review", actor_id
    )
    if owner_is_submitting:
        audit_service.log(
            db, caigo_approval_entity_type, assessment.id, "submitted_for_review", actor_id
        )


def approve_owner_stage(
    db: Session,
    assessment: ApprovableAssessment,
    actor_id: int | None,
    *,
    entity_label: str,
    owner_approval_entity_type: str,
    caigo_approval_entity_type: str,
    pending_owner_status: Any,
    pending_caigo_status: Any,
    require_ready: Callable[[], None] | None = None,
) -> None:
    if assessment.status != pending_owner_status:
        raise ConflictError(
            f"{entity_label} {assessment.id} must be pending owner approval, "
            f"currently '{assessment.status}'"
        )
    if require_ready is not None:
        require_ready()

    lifecycle = ai_system_lifecycle_service.get_or_create(db, assessment.ai_system_row_id)
    if actor_id is not None and actor_id != lifecycle.owner_id:
        raise AuthorizationError("Only this AI system's owner can approve this stage.")
    audit_service.require_different_approver(
        db, owner_approval_entity_type, assessment.id, actor_id
    )
    # Approving here always generates the CAIGO stage's own
    # "submitted_for_review" entry below, attributed to this same actor --
    # if they are the only person who could approve that stage, refuse now
    # rather than leave the record stuck there.
    governance_role_service.require_a_possible_approver(db, actor_id)

    if not claim_transition(
        db,
        assessment,
        expected_statuses=pending_owner_status,
        changes={
            "owner_approved_by": actor_id,
            "owner_approved_at": datetime.now(UTC),
            "status": pending_caigo_status,
        },
    ):
        _refuse(assessment, entity_label, "pending owner approval")

    audit_service.log(db, owner_approval_entity_type, assessment.id, "approved", actor_id)
    audit_service.log(
        db, caigo_approval_entity_type, assessment.id, "submitted_for_review", actor_id
    )


def approve_caigo_stage(
    db: Session,
    assessment: ApprovableAssessment,
    actor_id: int | None,
    *,
    entity_label: str,
    caigo_approval_entity_type: str,
    pending_caigo_status: Any,
    completed_status: Any,
    require_ready: Callable[[], None] | None = None,
) -> None:
    if assessment.status != pending_caigo_status:
        raise ConflictError(
            f"{entity_label} {assessment.id} must be pending CAIGO approval, "
            f"currently '{assessment.status}'"
        )
    if require_ready is not None:
        require_ready()

    governance_role_service.require_caigo(db, actor_id)
    audit_service.require_different_approver(
        db, caigo_approval_entity_type, assessment.id, actor_id
    )

    if not claim_transition(
        db,
        assessment,
        expected_statuses=pending_caigo_status,
        changes={
            "caigo_approved_by": actor_id,
            "caigo_approved_at": datetime.now(UTC),
            "status": completed_status,
            **completion_dates(assessment),
        },
    ):
        _refuse(assessment, entity_label, "pending CAIGO approval")

    audit_service.log(db, caigo_approval_entity_type, assessment.id, "approved", actor_id)
