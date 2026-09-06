from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.lifecycle_stages import LifecycleStage, label, next_stage
from app.dependencies import get_current_actor_id, get_current_approver_id
from app.models.ai_system_lifecycle import AISystemLifecycle
from app.schemas.ai_system_lifecycle import (
    AISystemLifecycleRead,
    ArchivedAISystemRead,
    DeploymentRecordUpdate,
    GateRequirementRead,
    MonitoringUpdate,
    OwnerUpdate,
    RetirementUpdate,
    StageRevert,
)
from app.services import (
    ai_system_inventory_service,
    ai_system_lifecycle_service,
    lifecycle_gate_service,
)

router = APIRouter(prefix="/ai-systems", tags=["ai-system-lifecycle"])


def _to_read(db: Session, lifecycle: AISystemLifecycle) -> AISystemLifecycleRead:
    requirements = lifecycle_gate_service.gate_requirements(
        db, lifecycle.ai_system_row_id, lifecycle
    )
    upcoming = next_stage(lifecycle.current_stage)
    return AISystemLifecycleRead(
        ai_system_row_id=lifecycle.ai_system_row_id,
        current_stage=lifecycle.current_stage,
        current_stage_label=label(lifecycle.current_stage),
        next_stage=str(upcoming) if upcoming else None,
        next_stage_label=label(upcoming) if upcoming else None,
        entered_stage_at=lifecycle.entered_stage_at,
        owner_id=lifecycle.owner_id,
        deployment_environment=lifecycle.deployment_environment,
        deployment_version=lifecycle.deployment_version,
        deployed_at=lifecycle.deployed_at,
        deployment_approved_by=lifecycle.deployment_approved_by,
        deployment_approved_at=lifecycle.deployment_approved_at,
        monitoring_owner_id=lifecycle.monitoring_owner_id,
        incident_escalation_path=lifecycle.incident_escalation_path,
        retirement_reason=lifecycle.retirement_reason,
        retirement_approved_by=lifecycle.retirement_approved_by,
        retirement_approved_at=lifecycle.retirement_approved_at,
        retired_at=lifecycle.retired_at,
        retention_until=lifecycle.retention_until,
        archived_at=lifecycle.archived_at,
        is_archived=lifecycle.archived_at is not None,
        retention_expired=ai_system_lifecycle_service.retention_expired(lifecycle),
        requirements=[GateRequirementRead(**vars(r)) for r in requirements],
        can_advance=upcoming is not None and all(r.satisfied for r in requirements),
        can_archive=(
            lifecycle.current_stage == LifecycleStage.RETIREMENT
            and lifecycle.archived_at is None
            and all(r.satisfied for r in requirements)
        ),
    )


# Declared before /{row_id}/... so the path param doesn't swallow "archive".
@router.get("/archive", response_model=list[ArchivedAISystemRead])
def list_archive(db: Session = Depends(get_db)) -> list[ArchivedAISystemRead]:
    """Retired systems, kept read-only until their retention date passes."""
    entries = []
    for row in ai_system_inventory_service.list_archived_rows(db):
        lifecycle = ai_system_lifecycle_service.get_or_create(db, row.id)
        name = row.data.get("name")
        entries.append(
            ArchivedAISystemRead(
                ai_system_row_id=row.id,
                name=str(name) if name else f"AI System #{row.id}",
                retirement_reason=lifecycle.retirement_reason,
                retired_at=lifecycle.retired_at,
                retention_until=lifecycle.retention_until,
                archived_at=lifecycle.archived_at,
                retention_expired=ai_system_lifecycle_service.retention_expired(lifecycle),
            )
        )
    return entries


@router.get("/{row_id}/lifecycle", response_model=AISystemLifecycleRead)
def get_lifecycle(row_id: int, db: Session = Depends(get_db)) -> AISystemLifecycleRead:
    return _to_read(db, ai_system_lifecycle_service.get_or_create(db, row_id))


@router.post("/{row_id}/lifecycle/advance", response_model=AISystemLifecycleRead)
def advance_stage(
    row_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AISystemLifecycleRead:
    return _to_read(db, ai_system_lifecycle_service.advance(db, row_id, actor_id))


@router.post("/{row_id}/lifecycle/revert", response_model=AISystemLifecycleRead)
def revert_stage(
    row_id: int,
    data: StageRevert,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AISystemLifecycleRead:
    lifecycle = ai_system_lifecycle_service.revert(db, row_id, data.reason, actor_id)
    return _to_read(db, lifecycle)


@router.put("/{row_id}/lifecycle/deployment-record", response_model=AISystemLifecycleRead)
def set_deployment_record(
    row_id: int,
    data: DeploymentRecordUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AISystemLifecycleRead:
    """Plain JSON so a CI/CD job can stamp the release it just shipped."""
    lifecycle = ai_system_lifecycle_service.set_deployment_record(
        db,
        row_id,
        data.deployment_environment,
        data.deployment_version,
        data.deployed_at,
        actor_id,
    )
    return _to_read(db, lifecycle)


@router.put("/{row_id}/lifecycle/monitoring", response_model=AISystemLifecycleRead)
def set_monitoring(
    row_id: int,
    data: MonitoringUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AISystemLifecycleRead:
    lifecycle = ai_system_lifecycle_service.set_monitoring(
        db, row_id, data.monitoring_owner_id, data.incident_escalation_path, actor_id
    )
    return _to_read(db, lifecycle)


@router.put("/{row_id}/lifecycle/owner", response_model=AISystemLifecycleRead)
def set_owner(
    row_id: int,
    data: OwnerUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AISystemLifecycleRead:
    lifecycle = ai_system_lifecycle_service.set_owner(db, row_id, data.owner_id, actor_id)
    return _to_read(db, lifecycle)


@router.post(
    "/{row_id}/lifecycle/request-deployment-approval", response_model=AISystemLifecycleRead
)
def request_deployment_approval(
    row_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AISystemLifecycleRead:
    ai_system_lifecycle_service.request_deployment_approval(db, row_id, actor_id)
    return _to_read(db, ai_system_lifecycle_service.get_or_create(db, row_id))


@router.post("/{row_id}/lifecycle/approve-deployment", response_model=AISystemLifecycleRead)
def approve_deployment(
    row_id: int,
    db: Session = Depends(get_db),
    actor_id: int = Depends(get_current_approver_id),
) -> AISystemLifecycleRead:
    return _to_read(db, ai_system_lifecycle_service.approve_deployment(db, row_id, actor_id))


@router.put("/{row_id}/lifecycle/retirement", response_model=AISystemLifecycleRead)
def set_retirement(
    row_id: int,
    data: RetirementUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AISystemLifecycleRead:
    lifecycle = ai_system_lifecycle_service.set_retirement(
        db, row_id, data.retirement_reason, data.retention_until, actor_id
    )
    return _to_read(db, lifecycle)


@router.post(
    "/{row_id}/lifecycle/request-retirement-approval", response_model=AISystemLifecycleRead
)
def request_retirement_approval(
    row_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AISystemLifecycleRead:
    ai_system_lifecycle_service.request_retirement_approval(db, row_id, actor_id)
    return _to_read(db, ai_system_lifecycle_service.get_or_create(db, row_id))


@router.post("/{row_id}/lifecycle/approve-retirement", response_model=AISystemLifecycleRead)
def approve_retirement(
    row_id: int,
    db: Session = Depends(get_db),
    actor_id: int = Depends(get_current_approver_id),
) -> AISystemLifecycleRead:
    return _to_read(db, ai_system_lifecycle_service.approve_retirement(db, row_id, actor_id))


@router.post("/{row_id}/lifecycle/archive", response_model=AISystemLifecycleRead)
def archive_system(
    row_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> AISystemLifecycleRead:
    return _to_read(db, ai_system_lifecycle_service.archive(db, row_id, actor_id))
