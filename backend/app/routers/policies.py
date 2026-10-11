from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id, get_current_approver_id
from app.schemas.policy import PolicyCreate, PolicyHistoryEntry, PolicyRead, PolicyUpdate
from app.schemas.staff import SharingUpdate
from app.services import policy_service

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=list[PolicyRead])
def list_policies(db: Session = Depends(get_db)) -> list[PolicyRead]:
    return policy_service.list_policies(db)


@router.post("", response_model=PolicyRead, status_code=201)
def create_policy(
    data: PolicyCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> PolicyRead:
    return policy_service.create_policy(db, data, actor_id)


@router.get("/{policy_id}", response_model=PolicyRead)
def get_policy(policy_id: int, db: Session = Depends(get_db)) -> PolicyRead:
    return policy_service.get_policy(db, policy_id)


@router.put("/{policy_id}", response_model=PolicyRead)
def update_policy(
    policy_id: int,
    data: PolicyUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> PolicyRead:
    return policy_service.update_policy(db, policy_id, data, actor_id)


@router.put("/{policy_id}/sharing", response_model=PolicyRead)
def set_sharing(
    policy_id: int,
    data: SharingUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> PolicyRead:
    return policy_service.set_sharing(db, policy_id, data.shared_with_employees, actor_id)


@router.delete("/{policy_id}", status_code=204)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    policy_service.delete_policy(db, policy_id, actor_id)


@router.post("/{policy_id}/submit-for-review", response_model=PolicyRead)
def submit_for_review(
    policy_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> PolicyRead:
    return policy_service.submit_for_review(db, policy_id, actor_id)


@router.post("/{policy_id}/approve", response_model=PolicyRead)
def approve_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    actor_id: int = Depends(get_current_approver_id),
) -> PolicyRead:
    return policy_service.approve_policy(db, policy_id, actor_id)


@router.post("/{policy_id}/retire", response_model=PolicyRead)
def retire_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    actor_id: int = Depends(get_current_approver_id),
) -> PolicyRead:
    return policy_service.retire_policy(db, policy_id, actor_id)


@router.get("/{policy_id}/versions", response_model=list[PolicyHistoryEntry])
def list_document_history(
    policy_id: int, db: Session = Depends(get_db)
) -> list[PolicyHistoryEntry]:
    return policy_service.list_document_history(db, policy_id)
