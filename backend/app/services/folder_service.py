from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.folder import Folder
from app.repositories import evidence_repository, folder_repository
from app.schemas.folder import FolderCreate, FolderUpdate
from app.services import audit_service


def _get_or_raise(db: Session, folder_id: int) -> Folder:
    folder = folder_repository.get(db, folder_id)
    if folder is None:
        raise NotFoundError("Folder", folder_id)
    return folder


def list_folders(
    db: Session, entity_type: str, entity_id: int, parent_folder_id: int | None
) -> list[Folder]:
    return folder_repository.list_at_level(db, entity_type, entity_id, parent_folder_id)


def get_folder(db: Session, folder_id: int) -> Folder:
    return _get_or_raise(db, folder_id)


def create_folder(db: Session, data: FolderCreate, actor_id: int | None) -> Folder:
    if data.parent_folder_id is not None:
        parent = _get_or_raise(db, data.parent_folder_id)
        if parent.entity_type != data.entity_type or parent.entity_id != data.entity_id:
            raise ValidationError(
                "parent_folder_id must belong to the same entity_type/entity_id"
            )

    folder = Folder(
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        parent_folder_id=data.parent_folder_id,
        name=data.name,
    )
    folder = folder_repository.create(db, folder)
    audit_service.log(db, data.entity_type, data.entity_id, "folder_created", actor_id, {
        "folder_id": folder.id,
        "name": folder.name,
    })
    return folder


def update_folder(db: Session, folder_id: int, data: FolderUpdate, actor_id: int | None) -> Folder:
    folder = _get_or_raise(db, folder_id)
    folder.name = data.name
    folder = folder_repository.save(db, folder)
    audit_service.log(
        db,
        folder.entity_type,
        folder.entity_id,
        "folder_renamed",
        actor_id,
        {"folder_id": folder.id},
    )
    return folder


def delete_folder(db: Session, folder_id: int, actor_id: int | None) -> None:
    folder = _get_or_raise(db, folder_id)
    if folder_repository.has_children(db, folder_id):
        raise ConflictError(f"Folder {folder_id} still contains subfolders; delete those first")
    if evidence_repository.has_evidence_in_folder(db, folder_id):
        raise ConflictError(f"Folder {folder_id} still contains documents; delete those first")

    folder_repository.delete(db, folder)
    audit_service.log(db, folder.entity_type, folder.entity_id, "folder_deleted", actor_id, {
        "folder_id": folder_id
    })
