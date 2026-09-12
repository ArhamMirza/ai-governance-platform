from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id, get_current_approver_id
from app.schemas.procedure import (
    ProcedureCreate,
    ProcedureHistoryEntry,
    ProcedureRead,
    ProcedureUpdate,
)
from app.services import procedure_service

router = APIRouter(prefix="/procedures", tags=["procedures"])


@router.get("", response_model=list[ProcedureRead])
def list_procedures(db: Session = Depends(get_db)) -> list[ProcedureRead]:
    return procedure_service.list_procedures(db)


@router.post("", response_model=ProcedureRead, status_code=201)
def create_procedure(
    data: ProcedureCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ProcedureRead:
    return procedure_service.create_procedure(db, data, actor_id)


@router.get("/{procedure_id}", response_model=ProcedureRead)
def get_procedure(procedure_id: int, db: Session = Depends(get_db)) -> ProcedureRead:
    return procedure_service.get_procedure(db, procedure_id)


@router.put("/{procedure_id}", response_model=ProcedureRead)
def update_procedure(
    procedure_id: int,
    data: ProcedureUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ProcedureRead:
    return procedure_service.update_procedure(db, procedure_id, data, actor_id)


@router.delete("/{procedure_id}", status_code=204)
def delete_procedure(
    procedure_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    procedure_service.delete_procedure(db, procedure_id, actor_id)


@router.post("/{procedure_id}/submit-for-review", response_model=ProcedureRead)
def submit_for_review(
    procedure_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> ProcedureRead:
    return procedure_service.submit_for_review(db, procedure_id, actor_id)


@router.post("/{procedure_id}/approve", response_model=ProcedureRead)
def approve_procedure(
    procedure_id: int,
    db: Session = Depends(get_db),
    actor_id: int = Depends(get_current_approver_id),
) -> ProcedureRead:
    return procedure_service.approve_procedure(db, procedure_id, actor_id)


@router.post("/{procedure_id}/retire", response_model=ProcedureRead)
def retire_procedure(
    procedure_id: int,
    db: Session = Depends(get_db),
    actor_id: int = Depends(get_current_approver_id),
) -> ProcedureRead:
    return procedure_service.retire_procedure(db, procedure_id, actor_id)


@router.get("/{procedure_id}/versions", response_model=list[ProcedureHistoryEntry])
def list_document_history(
    procedure_id: int, db: Session = Depends(get_db)
) -> list[ProcedureHistoryEntry]:
    return procedure_service.list_document_history(db, procedure_id)
