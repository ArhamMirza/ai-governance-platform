from sqlalchemy.orm import Session

from app.core.exceptions import InvalidStatusTransitionError, NotFoundError
from app.models.audit_log import AuditLogEntry
from app.models.policy import Policy, PolicyStatus
from app.repositories import audit_log_repository, policy_repository
from app.schemas.policy import PolicyCreate, PolicyUpdate
from app.services import audit_service, framework_service, governance_role_service

DOCUMENT_HISTORY_ACTIONS = ["document_added", "document_removed"]


def _get_or_raise(db: Session, policy_id: int) -> Policy:
    policy = policy_repository.get(db, policy_id)
    if policy is None:
        raise NotFoundError("Policy", policy_id)
    return policy


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
    policy.status = PolicyStatus.IN_REVIEW
    policy = policy_repository.save(db, policy)
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
    policy.status = PolicyStatus.APPROVED
    policy = policy_repository.save(db, policy)
    audit_service.log(db, "Policy", policy.id, "approved", actor_id)
    return policy


def delete_policy(db: Session, policy_id: int, actor_id: int | None) -> None:
    policy = _get_or_raise(db, policy_id)
    if policy.status != PolicyStatus.DRAFT:
        raise InvalidStatusTransitionError(
            f"Policy {policy_id} cannot be deleted while status is '{policy.status}'; "
            "only draft policies can be deleted"
        )
    policy_repository.delete(db, policy)
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
