from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id, get_current_approver_id
from app.models.corrective_action import CorrectiveAction
from app.schemas.corrective_action import (
    CorrectiveActionCreate,
    CorrectiveActionRead,
    CorrectiveActionUpdate,
)
from app.services import corrective_action_service, framework_service

router = APIRouter(prefix="/corrective-actions", tags=["corrective-actions"])


def _to_read(db: Session, corrective_action: CorrectiveAction) -> CorrectiveActionRead:
    framework_tags = framework_service.get_tags(
        db, corrective_action_service.ENTITY_TYPE, corrective_action.id
    )
    return CorrectiveActionRead(
        id=corrective_action.id,
        title=corrective_action.title,
        nonconformity_description=corrective_action.nonconformity_description,
        root_cause=corrective_action.root_cause,
        action_description=corrective_action.action_description,
        source_type=corrective_action.source_type,
        source_id=corrective_action.source_id,
        assignee_id=corrective_action.assignee_id,
        due_date=corrective_action.due_date,
        status=corrective_action.status,
        overdue=corrective_action_service.is_overdue(
            corrective_action.due_date, corrective_action.status, datetime.now(UTC).date()
        ),
        framework_tags=framework_tags,
        closed_by=corrective_action.closed_by,
        closed_at=corrective_action.closed_at,
        created_at=corrective_action.created_at,
        updated_at=corrective_action.updated_at,
    )


@router.get("", response_model=list[CorrectiveActionRead])
def list_corrective_actions(db: Session = Depends(get_db)) -> list[CorrectiveActionRead]:
    return [_to_read(db, ca) for ca in corrective_action_service.list_corrective_actions(db)]


@router.post("", response_model=CorrectiveActionRead, status_code=201)
def create_corrective_action(
    data: CorrectiveActionCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> CorrectiveActionRead:
    corrective_action = corrective_action_service.create_corrective_action(db, data, actor_id)
    return _to_read(db, corrective_action)


@router.get("/{corrective_action_id}", response_model=CorrectiveActionRead)
def get_corrective_action(
    corrective_action_id: int, db: Session = Depends(get_db)
) -> CorrectiveActionRead:
    return _to_read(db, corrective_action_service.get_corrective_action(db, corrective_action_id))


@router.put("/{corrective_action_id}", response_model=CorrectiveActionRead)
def update_corrective_action(
    corrective_action_id: int,
    data: CorrectiveActionUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> CorrectiveActionRead:
    corrective_action = corrective_action_service.update_corrective_action(
        db, corrective_action_id, data, actor_id
    )
    return _to_read(db, corrective_action)


@router.delete("/{corrective_action_id}", status_code=204)
def delete_corrective_action(
    corrective_action_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    corrective_action_service.delete_corrective_action(db, corrective_action_id, actor_id)


@router.post("/{corrective_action_id}/submit-for-verification", response_model=CorrectiveActionRead)
def submit_for_verification(
    corrective_action_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> CorrectiveActionRead:
    corrective_action = corrective_action_service.submit_for_verification(
        db, corrective_action_id, actor_id
    )
    return _to_read(db, corrective_action)


@router.post("/{corrective_action_id}/verify-and-close", response_model=CorrectiveActionRead)
def verify_and_close(
    corrective_action_id: int,
    db: Session = Depends(get_db),
    actor_id: int = Depends(get_current_approver_id),
) -> CorrectiveActionRead:
    corrective_action = corrective_action_service.verify_and_close(
        db, corrective_action_id, actor_id
    )
    return _to_read(db, corrective_action)


@router.post("/{corrective_action_id}/reopen", response_model=CorrectiveActionRead)
def reopen(
    corrective_action_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> CorrectiveActionRead:
    corrective_action = corrective_action_service.reopen(db, corrective_action_id, actor_id)
    return _to_read(db, corrective_action)
