from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core import review_cadence
from app.core.concurrency import claim_transition
from app.core.exceptions import ConflictError, InvalidStatusTransitionError, NotFoundError
from app.models.audit_log import AuditLogEntry
from app.models.policy import Policy, PolicyStatus
from app.models.procedure import ProcedureStatus
from app.repositories import audit_log_repository, policy_repository, procedure_repository
from app.schemas.policy import PolicyCreate, PolicyUpdate
from app.services import audit_service, framework_service, governance_role_service

DOCUMENT_HISTORY_ACTIONS = ["document_added", "document_removed"]


def _get_or_raise(db: Session, policy_id: int) -> Policy:
    policy = policy_repository.get(db, policy_id)
    if policy is None:
        raise NotFoundError("Policy", policy_id)
    return policy


def _claim(db: Session, policy: Policy, expected: str, changes: dict) -> None:
    """Each status check above ran in a transaction of its own, so two
    simultaneous callers can both pass it. Re-stating the expected status in
    the write is what makes only one of them land."""
    if not claim_transition(db, policy, expected_statuses=expected, changes=changes):
        raise InvalidStatusTransitionError(
            f"Policy {policy.id} is no longer '{expected}' -- someone else has "
            f"already moved it on, and it is now '{policy.status}'."
        )


def list_policies(db: Session) -> list[Policy]:
    return policy_repository.list_all(db)


def get_policy(db: Session, policy_id: int) -> Policy:
    return _get_or_raise(db, policy_id)


def create_policy(db: Session, data: PolicyCreate, actor_id: int | None) -> Policy:
    policy = Policy(
        title=data.title,
        description=data.description,
        owner_id=data.owner_id,
        effective_date=data.effective_date,
        status=PolicyStatus.DRAFT,
        version=1,
    )
    policy = policy_repository.create(db, policy)
    audit_service.log(db, "Policy", policy.id, "created", actor_id, {"title": policy.title})
    return policy


def update_policy(
    db: Session, policy_id: int, data: PolicyUpdate, actor_id: int | None
) -> Policy:
    policy = _get_or_raise(db, policy_id)
    if policy.status != PolicyStatus.DRAFT:
        raise InvalidStatusTransitionError(
            f"Policy {policy_id} cannot be edited while status is '{policy.status}'; "
            "only draft policies can be edited"
        )

    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(policy, field, value)

    policy = policy_repository.save(db, policy)
    audit_service.log(db, "Policy", policy.id, "updated", actor_id, changes)
    return policy


def submit_for_review(db: Session, policy_id: int, actor_id: int | None) -> Policy:
    policy = _get_or_raise(db, policy_id)
    if policy.status != PolicyStatus.DRAFT:
        raise InvalidStatusTransitionError(
            f"Policy {policy_id} must be in 'draft' status to submit for review, "
            f"currently '{policy.status}'"
        )
    _claim(db, policy, PolicyStatus.DRAFT, {"status": PolicyStatus.IN_REVIEW})
    audit_service.log(db, "Policy", policy.id, "submitted_for_review", actor_id)
    return policy


def approve_policy(db: Session, policy_id: int, actor_id: int | None) -> Policy:
    policy = _get_or_raise(db, policy_id)
    if policy.status != PolicyStatus.IN_REVIEW:
        raise InvalidStatusTransitionError(
            f"Policy {policy_id} must be in 'in_review' status to approve, "
            f"currently '{policy.status}'"
        )
    governance_role_service.require_caigo(db, actor_id)
    audit_service.require_different_approver(db, "Policy", policy_id, actor_id)
    _claim(
        db,
        policy,
        PolicyStatus.IN_REVIEW,
        {
            "status": PolicyStatus.APPROVED,
            # Approval schedules the next review rather than being the end of
            # it -- same cadence the assessments use.
            "next_review_date": review_cadence.next_review_date(datetime.now(UTC).date()),
        },
    )
    audit_service.log(db, "Policy", policy.id, "approved", actor_id)
    return policy


def retire_policy(db: Session, policy_id: int, actor_id: int | None) -> Policy:
    """Stands an approved policy down once it has been superseded. Kept rather
    than deleted so the record of what governed the organization, and when,
    stays intact -- the same reasoning behind archiving a retired AI system."""
    policy = _get_or_raise(db, policy_id)
    if policy.status != PolicyStatus.APPROVED:
        raise InvalidStatusTransitionError(
            f"Policy {policy_id} must be in 'approved' status to retire, "
            f"currently '{policy.status}'"
        )
    governance_role_service.require_caigo(db, actor_id)
    # A procedure implements its policy, so standing the policy down while
    # live procedures still point at it would leave them governed by something
    # that has been withdrawn. Refused rather than cascaded, so retiring an
    # approved procedure stays a deliberate act -- the same way delete_role
    # refuses a role that still has roles reporting to it.
    live_procedures = [
        procedure
        for procedure in procedure_repository.list_for_policy(db, policy_id)
        if procedure.status != ProcedureStatus.RETIRED
    ]
    if live_procedures:
        titles = ", ".join(procedure.title for procedure in live_procedures)
        raise ConflictError(
            f"'{policy.title}' still has procedures implementing it ({titles}); "
            "retire those first."
        )

    _claim(db, policy, PolicyStatus.APPROVED, {"status": PolicyStatus.RETIRED})
    audit_service.log(db, "Policy", policy.id, "retired", actor_id)
    return policy


def delete_policy(db: Session, policy_id: int, actor_id: int | None) -> None:
    # Imported here rather than at module scope: evidence_service imports
    # this module (to bump a draft's version when its documents change), so
    # a top-level import back would be circular.
    from app.services import evidence_service

    policy = _get_or_raise(db, policy_id)
    if policy.status != PolicyStatus.DRAFT:
        raise InvalidStatusTransitionError(
            f"Policy {policy_id} cannot be deleted while status is '{policy.status}'; "
            "only draft policies can be deleted"
        )
    policy_repository.delete(db, policy)
    evidence_service.delete_all_for_entity(db, "Policy", policy_id)
    framework_service.delete_tags(db, "Policy", policy_id)
    audit_service.log(db, "Policy", policy_id, "deleted", actor_id)


def list_document_history(db: Session, policy_id: int) -> list[AuditLogEntry]:
    _get_or_raise(db, policy_id)
    return audit_log_repository.list_for_entity(db, "Policy", policy_id, DOCUMENT_HISTORY_ACTIONS)


def bump_version_if_draft(db: Session, policy_id: int) -> None:
    policy = policy_repository.get(db, policy_id)
    if policy is not None and policy.status == PolicyStatus.DRAFT:
        policy.version += 1
        policy_repository.save(db, policy)
