"""Moving an AI system through its life cycle, one gated stage at a time."""

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core.concurrency import claim_if_unset, create_or_get
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.lifecycle_stages import LifecycleStage, label, next_stage, previous_stage
from app.models.ai_system_lifecycle import AISystemLifecycle
from app.repositories import ai_system_lifecycle_repository, sheet_repository
from app.services import (
    audit_service,
    governance_role_service,
    lifecycle_gate_service,
    organization_context_service,
)

ENTITY_TYPE = "AISystem"
# A distinct entity type per sign-off, so the segregation-of-duties lookup for
# a release approval never sees a retirement approval (or vice versa).
DEPLOYMENT_APPROVAL_ENTITY_TYPE = "AISystemDeploymentApproval"
RETIREMENT_APPROVAL_ENTITY_TYPE = "AISystemRetirementApproval"

STAGE_COLUMN_KEY = "lifecycle_stage"


def _validate_ai_system_row(db: Session, ai_system_row_id: int) -> None:
    from app.services import ai_system_inventory_service

    inventory_sheet = ai_system_inventory_service.get_or_create_sheet(db)
    row = sheet_repository.get_row(db, ai_system_row_id)
    if row is None or row.sheet_id != inventory_sheet.id:
        raise NotFoundError("AISystemRow", ai_system_row_id)


def _require_not_archived(lifecycle: AISystemLifecycle) -> None:
    """Once a system is archived, its life cycle record is meant to stay
    exactly as it was signed off -- archive()'s own docstring promises it is
    "kept read-only until the retention date passes." Every mutator below
    calls this first: without it, anyone with edit rights could rewrite the
    retention date on an already-archived system (making it read as expired
    on the spot) or revert its stage, defeating the one guarantee retention
    exists to make. Deleting the row is the sole exception, and it is gated
    on retention_expired instead, in ai_system_inventory_service.delete_row."""
    if lifecycle.archived_at is not None:
        raise ConflictError("This system is archived; its life cycle record can't be changed.")


def get_or_create(db: Session, ai_system_row_id: int) -> AISystemLifecycle:
    """Every AI system has a life cycle; one is created at Inception on first
    request. Lazy rather than eager so systems that predate this feature --
    and rows recreated by an inventory CSV import -- are covered too."""
    _validate_ai_system_row(db, ai_system_row_id)
    existing = ai_system_lifecycle_repository.get_for_ai_system(db, ai_system_row_id)
    if existing is not None:
        return existing
    # Two simultaneous first requests both get here; the unique constraint on
    # ai_system_row_id lets one through and hands the other the row it made.
    lifecycle = create_or_get(
        db,
        lambda: AISystemLifecycle(
            ai_system_row_id=ai_system_row_id, current_stage=LifecycleStage.INCEPTION
        ),
        lambda: ai_system_lifecycle_repository.get_for_ai_system(db, ai_system_row_id),
    )
    _write_stage_to_inventory(db, ai_system_row_id, lifecycle.current_stage)
    return lifecycle


def _write_stage_to_inventory(db: Session, ai_system_row_id: int, stage: str) -> None:
    """Mirror the stage into the inventory sheet cell so the grid and the
    xlsx export stay truthful. The cell is server-owned -- see
    ai_system_inventory_service.update_row."""
    row = sheet_repository.get_row(db, ai_system_row_id)
    if row is None:
        return
    row.data = {**row.data, STAGE_COLUMN_KEY: stage}
    sheet_repository.save_row(db, row)


def requirements(db: Session, ai_system_row_id: int) -> list:
    lifecycle = get_or_create(db, ai_system_row_id)
    return lifecycle_gate_service.gate_requirements(db, ai_system_row_id, lifecycle)


def advance(db: Session, ai_system_row_id: int, actor_id: int | None) -> AISystemLifecycle:
    lifecycle = get_or_create(db, ai_system_row_id)
    target = next_stage(lifecycle.current_stage)
    if target is None:
        raise ConflictError(
            f"{label(lifecycle.current_stage)} is the final stage of the life cycle."
        )

    outstanding = lifecycle_gate_service.unmet(
        lifecycle_gate_service.gate_requirements(db, ai_system_row_id, lifecycle)
    )
    if outstanding:
        raise ValidationError(
            f"Cannot leave {label(lifecycle.current_stage)} yet: "
            + "; ".join(requirement.detail for requirement in outstanding)
        )

    previous = lifecycle.current_stage
    lifecycle.current_stage = target
    lifecycle.entered_stage_at = datetime.now(UTC)
    lifecycle = ai_system_lifecycle_repository.save(db, lifecycle)
    _write_stage_to_inventory(db, ai_system_row_id, target)
    audit_service.log(
        db,
        ENTITY_TYPE,
        ai_system_row_id,
        "stage_advanced",
        actor_id,
        {"from": previous, "to": str(target)},
    )
    return lifecycle


def revert(
    db: Session, ai_system_row_id: int, reason: str, actor_id: int | None
) -> AISystemLifecycle:
    """Step back one stage -- a system that turns out not to be ready. The
    reason is recorded, and a release approval does not survive the trip."""
    if not reason.strip():
        raise ValidationError("Give a reason for moving this system back a stage.")

    lifecycle = get_or_create(db, ai_system_row_id)
    _require_not_archived(lifecycle)
    target = previous_stage(lifecycle.current_stage)
    if target is None:
        raise ConflictError(
            f"{label(lifecycle.current_stage)} is the first stage of the life cycle."
        )

    previous = lifecycle.current_stage
    if previous == LifecycleStage.DEPLOYMENT:
        lifecycle.deployment_approved_by = None
        lifecycle.deployment_approved_at = None

    lifecycle.current_stage = target
    lifecycle.entered_stage_at = datetime.now(UTC)
    lifecycle = ai_system_lifecycle_repository.save(db, lifecycle)
    _write_stage_to_inventory(db, ai_system_row_id, target)
    audit_service.log(
        db,
        ENTITY_TYPE,
        ai_system_row_id,
        "stage_reverted",
        actor_id,
        {"from": previous, "to": str(target), "reason": reason},
    )
    return lifecycle


def set_deployment_record(
    db: Session,
    ai_system_row_id: int,
    environment: str | None,
    version: str | None,
    deployed_at: date | None,
    actor_id: int | None,
) -> AISystemLifecycle:
    lifecycle = get_or_create(db, ai_system_row_id)
    _require_not_archived(lifecycle)
    lifecycle.deployment_environment = environment
    lifecycle.deployment_version = version
    lifecycle.deployed_at = deployed_at
    lifecycle = ai_system_lifecycle_repository.save(db, lifecycle)
    audit_service.log(
        db,
        ENTITY_TYPE,
        ai_system_row_id,
        "deployment_record_updated",
        actor_id,
        {"environment": environment, "version": version},
    )
    return lifecycle


def set_monitoring(
    db: Session,
    ai_system_row_id: int,
    monitoring_owner_id: int | None,
    incident_escalation_path: str | None,
    actor_id: int | None,
) -> AISystemLifecycle:
    lifecycle = get_or_create(db, ai_system_row_id)
    _require_not_archived(lifecycle)
    lifecycle.monitoring_owner_id = monitoring_owner_id
    lifecycle.incident_escalation_path = incident_escalation_path
    lifecycle = ai_system_lifecycle_repository.save(db, lifecycle)
    audit_service.log(
        db,
        ENTITY_TYPE,
        ai_system_row_id,
        "monitoring_updated",
        actor_id,
        {"monitoring_owner_id": monitoring_owner_id},
    )
    return lifecycle


def effective_ai_roles(db: Session, lifecycle: AISystemLifecycle) -> list[str]:
    """This system's own AI roles if it has any set, else the
    organization's."""
    if lifecycle.ai_roles is not None:
        return lifecycle.ai_roles
    return organization_context_service.current_ai_roles(db)


def set_ai_roles(
    db: Session,
    ai_system_row_id: int,
    ai_roles: list[str] | None,
    actor_id: int | None,
) -> AISystemLifecycle:
    """None goes back to following the organization's roles."""
    lifecycle = get_or_create(db, ai_system_row_id)
    _require_not_archived(lifecycle)
    lifecycle.ai_roles = (
        None if ai_roles is None else organization_context_service.validated_ai_roles(ai_roles)
    )
    lifecycle = ai_system_lifecycle_repository.save(db, lifecycle)
    audit_service.log(
        db,
        ENTITY_TYPE,
        ai_system_row_id,
        "ai_roles_updated",
        actor_id,
        {"ai_roles": lifecycle.ai_roles},
    )
    return lifecycle


def set_owner(
    db: Session,
    ai_system_row_id: int,
    owner_id: int | None,
    actor_id: int | None,
) -> AISystemLifecycle:
    lifecycle = get_or_create(db, ai_system_row_id)
    _require_not_archived(lifecycle)
    lifecycle.owner_id = owner_id
    lifecycle = ai_system_lifecycle_repository.save(db, lifecycle)
    audit_service.log(
        db, ENTITY_TYPE, ai_system_row_id, "owner_updated", actor_id, {"owner_id": owner_id}
    )
    return lifecycle


def request_deployment_approval(db: Session, ai_system_row_id: int, actor_id: int | None) -> None:
    _require_not_archived(get_or_create(db, ai_system_row_id))
    # If the requester is the sole possible CAIGO approver, refuse now rather
    # than leave the release stuck waiting on an approval nobody can give --
    # see policy_service.submit_for_review for the same guard's origin.
    governance_role_service.require_a_possible_approver(db, actor_id)
    audit_service.log(
        db,
        DEPLOYMENT_APPROVAL_ENTITY_TYPE,
        ai_system_row_id,
        "submitted_for_review",
        actor_id,
    )


def approve_deployment(
    db: Session, ai_system_row_id: int, actor_id: int | None
) -> AISystemLifecycle:
    """Whoever requested the release can't be the one who approves it -- the
    same rule policies and procedures already enforce."""
    lifecycle = get_or_create(db, ai_system_row_id)
    _require_not_archived(lifecycle)
    governance_role_service.require_caigo(db, actor_id)
    try:
        audit_service.require_different_approver(
            db, DEPLOYMENT_APPROVAL_ENTITY_TYPE, ai_system_row_id, actor_id
        )
    except ConflictError as exc:
        # The shared helper names the internal entity type, which means
        # nothing to whoever is looking at the release approval screen.
        raise ConflictError(
            "You requested this release, so someone else has to approve it."
        ) from exc
    # Guarded on the approval still being open. There was no such check at
    # all before: approving twice simply overwrote whoever signed off first,
    # which two simultaneous approvers would do to each other and one
    # repeated click would do on its own. Moving the system back a stage
    # clears the approval, so a genuine re-release can be approved again.
    if not claim_if_unset(
        db,
        lifecycle,
        column="deployment_approved_by",
        changes={
            "deployment_approved_by": actor_id,
            "deployment_approved_at": datetime.now(UTC),
        },
    ):
        raise ConflictError("This release has already been approved.")

    audit_service.log(db, DEPLOYMENT_APPROVAL_ENTITY_TYPE, ai_system_row_id, "approved", actor_id)
    return lifecycle


def set_retirement(
    db: Session,
    ai_system_row_id: int,
    retirement_reason: str | None,
    retention_until: date | None,
    actor_id: int | None,
) -> AISystemLifecycle:
    lifecycle = get_or_create(db, ai_system_row_id)
    _require_not_archived(lifecycle)
    lifecycle.retirement_reason = retirement_reason
    lifecycle.retention_until = retention_until
    lifecycle = ai_system_lifecycle_repository.save(db, lifecycle)
    audit_service.log(
        db,
        ENTITY_TYPE,
        ai_system_row_id,
        "retirement_details_updated",
        actor_id,
        {"retention_until": str(retention_until) if retention_until else None},
    )
    return lifecycle


def request_retirement_approval(db: Session, ai_system_row_id: int, actor_id: int | None) -> None:
    _require_not_archived(get_or_create(db, ai_system_row_id))
    governance_role_service.require_a_possible_approver(db, actor_id)
    audit_service.log(
        db,
        RETIREMENT_APPROVAL_ENTITY_TYPE,
        ai_system_row_id,
        "submitted_for_review",
        actor_id,
    )


def approve_retirement(
    db: Session, ai_system_row_id: int, actor_id: int | None
) -> AISystemLifecycle:
    lifecycle = get_or_create(db, ai_system_row_id)
    _require_not_archived(lifecycle)
    governance_role_service.require_caigo(db, actor_id)
    try:
        audit_service.require_different_approver(
            db, RETIREMENT_APPROVAL_ENTITY_TYPE, ai_system_row_id, actor_id
        )
    except ConflictError as exc:
        raise ConflictError(
            "You requested this retirement, so someone else has to approve it."
        ) from exc
    # Same guard, same reason as approve_deployment.
    if not claim_if_unset(
        db,
        lifecycle,
        column="retirement_approved_by",
        changes={
            "retirement_approved_by": actor_id,
            "retirement_approved_at": datetime.now(UTC),
        },
    ):
        raise ConflictError("This retirement has already been approved.")

    audit_service.log(db, RETIREMENT_APPROVAL_ENTITY_TYPE, ai_system_row_id, "approved", actor_id)
    return lifecycle


def archive(db: Session, ai_system_row_id: int, actor_id: int | None) -> AISystemLifecycle:
    """Completes retirement. The system leaves the active inventory, and its
    record -- assessments, evidence, audit trail -- is kept read-only until
    the retention date passes."""
    lifecycle = get_or_create(db, ai_system_row_id)
    if lifecycle.current_stage != LifecycleStage.RETIREMENT:
        raise ConflictError("Only a system at the Retirement stage can be archived.")
    if lifecycle.archived_at is not None:
        raise ConflictError("This system is already archived.")

    outstanding = lifecycle_gate_service.unmet(
        lifecycle_gate_service.gate_requirements(db, ai_system_row_id, lifecycle)
    )
    if outstanding:
        raise ValidationError(
            "Cannot archive this system yet: "
            + "; ".join(requirement.detail for requirement in outstanding)
        )

    now = datetime.now(UTC)
    lifecycle.archived_at = now
    lifecycle.retired_at = now.date()
    lifecycle = ai_system_lifecycle_repository.save(db, lifecycle)
    audit_service.log(
        db,
        ENTITY_TYPE,
        ai_system_row_id,
        "archived",
        actor_id,
        {"retention_until": str(lifecycle.retention_until)},
    )
    return lifecycle


def is_archived(db: Session, ai_system_row_id: int) -> bool:
    lifecycle = ai_system_lifecycle_repository.get_for_ai_system(db, ai_system_row_id)
    return lifecycle is not None and lifecycle.archived_at is not None


def retention_expired(lifecycle: AISystemLifecycle, today: date | None = None) -> bool:
    """An archived record whose retention period has run out -- it can be
    deleted, and the dashboard says so."""
    if lifecycle.archived_at is None or lifecycle.retention_until is None:
        return False
    return lifecycle.retention_until < (today or datetime.now(UTC).date())


def delete_for_ai_system(db: Session, ai_system_row_id: int) -> None:
    ai_system_lifecycle_repository.delete_for_ai_system(db, ai_system_row_id)
