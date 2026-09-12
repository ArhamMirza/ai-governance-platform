"""The two-stage approval chain (this AI system's Owner, then the Chief AI
Governance Officer) that risk_assessment_service and impact_assessment_service
both run against their own model. Extracted here so the chain's actual rules
-- an AI system with no owner assigned can't be submitted; the owner
auto-skips straight to the CAIGO stage if they're also the one submitting;
no one approves their own submission -- live in one place instead of being
kept in lockstep by hand across two near-identical services.

Each caller passes in its own model instance, status values, and audit
entity-type strings; this module mutates the instance's approval fields in
place and raises the same exceptions either service already raised. The
caller still owns fetching/saving the record and logging its own
entity-type "submitted_for_review" audit entry, exactly as it did before
this was extracted -- only the shared approval logic moved."""

from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.core import review_cadence
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


def stamp_completed(assessment: ApprovableAssessment) -> None:
    """Completing an assessment stamps when it happened and when it's next
    due, so the review cadence can't be left unset by accident."""
    if assessment.assessment_date is None:
        assessment.assessment_date = datetime.now(UTC).date()
    assessment.next_review_date = review_cadence.next_review_date(assessment.assessment_date)


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

    assessment.status = draft_status
    assessment.owner_approved_by = None
    assessment.owner_approved_at = None
    assessment.caigo_approved_by = None
    assessment.caigo_approved_at = None
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
) -> None:
    """Implementation Team submits their work. If the AI system's owner is
    the one submitting, they can't meaningfully approve their own work, so
    this skips straight to the CAIGO stage instead of waiting on them."""
    if assessment.status not in pre_approval_statuses:
        raise ConflictError(
            f"{entity_label} {assessment.id} must be {pre_approval_label} to "
            f"submit for approval, currently '{assessment.status}'"
        )

    lifecycle = ai_system_lifecycle_service.get_or_create(db, assessment.ai_system_row_id)
    owner_id = lifecycle.owner_id
    if owner_id is None:
        raise ValidationError(
            "This AI system has no owner assigned yet -- assign an AI System "
            "Owner before submitting for approval, or the owner stage can "
            "never be approved."
        )

    audit_service.log(
        db, owner_approval_entity_type, assessment.id, "submitted_for_review", actor_id
    )
    if actor_id == owner_id:
        assessment.status = pending_caigo_status
        audit_service.log(
            db, caigo_approval_entity_type, assessment.id, "submitted_for_review", actor_id
        )
    else:
        assessment.status = pending_owner_status


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
) -> None:
    if assessment.status != pending_owner_status:
        raise ConflictError(
            f"{entity_label} {assessment.id} must be pending owner approval, "
            f"currently '{assessment.status}'"
        )

    lifecycle = ai_system_lifecycle_service.get_or_create(db, assessment.ai_system_row_id)
    if actor_id is not None and actor_id != lifecycle.owner_id:
        raise AuthorizationError("Only this AI system's owner can approve this stage.")
    audit_service.require_different_approver(
        db, owner_approval_entity_type, assessment.id, actor_id
    )

    assessment.owner_approved_by = actor_id
    assessment.owner_approved_at = datetime.now(UTC)
    assessment.status = pending_caigo_status
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
) -> None:
    if assessment.status != pending_caigo_status:
        raise ConflictError(
            f"{entity_label} {assessment.id} must be pending CAIGO approval, "
            f"currently '{assessment.status}'"
        )

    governance_role_service.require_caigo(db, actor_id)
    audit_service.require_different_approver(
        db, caigo_approval_entity_type, assessment.id, actor_id
    )

    assessment.caigo_approved_by = actor_id
    assessment.caigo_approved_at = datetime.now(UTC)
    assessment.status = completed_status
    stamp_completed(assessment)
    audit_service.log(db, caigo_approval_entity_type, assessment.id, "approved", actor_id)
