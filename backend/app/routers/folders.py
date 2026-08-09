from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.schemas.folder import FolderCreate, FolderRead, FolderUpdate
from app.services import folder_service

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get("", response_model=list[FolderRead])
def list_folders(
    entity_type: str,
    entity_id: int,
    parent_folder_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[FolderRead]:
    return folder_service.list_folders(db, entity_type, entity_id, parent_folder_id)


@router.post("", response_model=FolderRead, status_code=201)
def create_folder(
    data: FolderCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> FolderRead:
    return folder_service.create_folder(db, data, actor_id)


@router.get("/{folder_id}", response_model=FolderRead)
def get_folder(folder_id: int, db: Session = Depends(get_db)) -> FolderRead:
    return folder_service.get_folder(db, folder_id)


@router.put("/{folder_id}", response_model=FolderRead)
def update_folder(
    folder_id: int,
    data: FolderUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> FolderRead:
    return folder_service.update_folder(db, folder_id, data, actor_id)


@router.delete("/{folder_id}", status_code=204)
def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    folder_service.delete_folder(db, folder_id, actor_id)
