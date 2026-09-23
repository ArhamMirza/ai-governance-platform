from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core import review_cadence
from app.core.concurrency import claim_transition
from app.core.exceptions import InvalidStatusTransitionError, NotFoundError
from app.models.audit_log import AuditLogEntry
from app.models.procedure import Procedure, ProcedureStatus
from app.repositories import audit_log_repository, policy_repository, procedure_repository
from app.schemas.procedure import ProcedureCreate, ProcedureUpdate
from app.services import audit_service, framework_service, governance_role_service

DOCUMENT_HISTORY_ACTIONS = ["document_added", "document_removed"]


def _get_or_raise(db: Session, procedure_id: int) -> Procedure:
    procedure = procedure_repository.get(db, procedure_id)
    if procedure is None:
        raise NotFoundError("Procedure", procedure_id)
    return procedure


def _claim(db: Session, procedure: Procedure, expected: str, changes: dict) -> None:
    """Each status check above ran in a transaction of its own, so two
    simultaneous callers can both pass it -- see policy_service._claim."""
    if not claim_transition(db, procedure, expected_statuses=expected, changes=changes):
        raise InvalidStatusTransitionError(
            f"Procedure {procedure.id} is no longer '{expected}' -- someone else "
            f"has already moved it on, and it is now '{procedure.status}'."
        )


def _validate_policy_link(db: Session, policy_id: int | None) -> None:
    if policy_id is not None and policy_repository.get(db, policy_id) is None:
        raise NotFoundError("Policy", policy_id)


def list_procedures(db: Session) -> list[Procedure]:
    return procedure_repository.list_all(db)


def get_procedure(db: Session, procedure_id: int) -> Procedure:
    return _get_or_raise(db, procedure_id)


def create_procedure(db: Session, data: ProcedureCreate, actor_id: int | None) -> Procedure:
    _validate_policy_link(db, data.policy_id)
    procedure = Procedure(
        title=data.title,
        description=data.description,
        owner_id=data.owner_id,
        policy_id=data.policy_id,
        effective_date=data.effective_date,
        status=ProcedureStatus.DRAFT,
        version=1,
    )
    procedure = procedure_repository.create(db, procedure)
    audit_service.log(
        db, "Procedure", procedure.id, "created", actor_id, {"title": procedure.title}
    )
    return procedure


def update_procedure(
    db: Session, procedure_id: int, data: ProcedureUpdate, actor_id: int | None
) -> Procedure:
    procedure = _get_or_raise(db, procedure_id)
    if procedure.status != ProcedureStatus.DRAFT:
        raise InvalidStatusTransitionError(
            f"Procedure {procedure_id} cannot be edited while status is '{procedure.status}'; "
            "only draft procedures can be edited"
        )

    changes = data.model_dump(exclude_unset=True)
    if "policy_id" in changes:
        _validate_policy_link(db, changes["policy_id"])
    for field, value in changes.items():
        setattr(procedure, field, value)

    procedure = procedure_repository.save(db, procedure)
    audit_service.log(db, "Procedure", procedure.id, "updated", actor_id, changes)
    return procedure


def submit_for_review(db: Session, procedure_id: int, actor_id: int | None) -> Procedure:
    procedure = _get_or_raise(db, procedure_id)
    if procedure.status != ProcedureStatus.DRAFT:
        raise InvalidStatusTransitionError(
            f"Procedure {procedure_id} must be in 'draft' status to submit for review, "
            f"currently '{procedure.status}'"
        )
    governance_role_service.require_a_possible_approver(db, actor_id)
    _claim(db, procedure, ProcedureStatus.DRAFT, {"status": ProcedureStatus.IN_REVIEW})
    audit_service.log(db, "Procedure", procedure.id, "submitted_for_review", actor_id)
    return procedure


def approve_procedure(db: Session, procedure_id: int, actor_id: int | None) -> Procedure:
    procedure = _get_or_raise(db, procedure_id)
    if procedure.status != ProcedureStatus.IN_REVIEW:
        raise InvalidStatusTransitionError(
            f"Procedure {procedure_id} must be in 'in_review' status to approve, "
            f"currently '{procedure.status}'"
        )
    governance_role_service.require_caigo(db, actor_id)
    audit_service.require_different_approver(db, "Procedure", procedure_id, actor_id)
    _claim(
        db,
        procedure,
        ProcedureStatus.IN_REVIEW,
        {
            "status": ProcedureStatus.APPROVED,
            # Approval schedules the next review rather than being the end of
            # it -- same cadence policies and the assessments use.
            "next_review_date": review_cadence.next_review_date(datetime.now(UTC).date()),
        },
    )
    audit_service.log(db, "Procedure", procedure.id, "approved", actor_id)
    return procedure


def retire_procedure(db: Session, procedure_id: int, actor_id: int | None) -> Procedure:
    """Stands an approved procedure down once it has been superseded -- see
    policy_service.retire_policy."""
    procedure = _get_or_raise(db, procedure_id)
    if procedure.status != ProcedureStatus.APPROVED:
        raise InvalidStatusTransitionError(
            f"Procedure {procedure_id} must be in 'approved' status to retire, "
            f"currently '{procedure.status}'"
        )
    governance_role_service.require_caigo(db, actor_id)
    _claim(db, procedure, ProcedureStatus.APPROVED, {"status": ProcedureStatus.RETIRED})
    audit_service.log(db, "Procedure", procedure.id, "retired", actor_id)
    return procedure


def delete_procedure(db: Session, procedure_id: int, actor_id: int | None) -> None:
    procedure = _get_or_raise(db, procedure_id)
    if procedure.status != ProcedureStatus.DRAFT:
        raise InvalidStatusTransitionError(
            f"Procedure {procedure_id} cannot be deleted while status is '{procedure.status}'; "
            "only draft procedures can be deleted"
        )
    # Imported here rather than at module scope: evidence_service imports
    # this module (to bump a draft's version when its documents change), so
    # a top-level import back would be circular.
    from app.services import evidence_service

    procedure_repository.delete(db, procedure)
    evidence_service.delete_all_for_entity(db, "Procedure", procedure_id)
    framework_service.delete_tags(db, "Procedure", procedure_id)
    audit_service.log(db, "Procedure", procedure_id, "deleted", actor_id)


def list_document_history(db: Session, procedure_id: int) -> list[AuditLogEntry]:
    _get_or_raise(db, procedure_id)
    return audit_log_repository.list_for_entity(
        db, "Procedure", procedure_id, DOCUMENT_HISTORY_ACTIONS
    )


def bump_version_if_draft(db: Session, procedure_id: int) -> None:
    procedure = procedure_repository.get(db, procedure_id)
    if procedure is not None and procedure.status == ProcedureStatus.DRAFT:
        procedure.version += 1
        procedure_repository.save(db, procedure)
