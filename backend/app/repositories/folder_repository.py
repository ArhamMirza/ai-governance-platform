from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.folder import Folder


def get(db: Session, folder_id: int) -> Folder | None:
    return db.get(Folder, folder_id)


def list_at_level(
    db: Session, entity_type: str, entity_id: int, parent_folder_id: int | None
) -> list[Folder]:
    return list(
        db.scalars(
            select(Folder)
            .where(
                Folder.entity_type == entity_type,
                Folder.entity_id == entity_id,
                Folder.parent_folder_id == parent_folder_id,
            )
            .order_by(Folder.name)
        )
    )


def create(db: Session, folder: Folder) -> Folder:
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


def save(db: Session, folder: Folder) -> Folder:
    db.commit()
    db.refresh(folder)
    return folder


def delete(db: Session, folder: Folder) -> None:
    db.delete(folder)
    db.commit()


def has_children(db: Session, folder_id: int) -> bool:
    return db.scalar(select(Folder.id).where(Folder.parent_folder_id == folder_id)) is not None


def delete_all_for_entity(db: Session, entity_type: str, entity_id: int) -> None:
    """Drops every folder for an entity that is itself being deleted.

    entity_type/entity_id are stored on every folder row directly, not just
    the root one, so this needs no recursive walk down the tree -- one query
    already reaches every folder that belongs to this entity, at any depth."""
    folders = list(
        db.scalars(
            select(Folder).where(
                Folder.entity_type == entity_type, Folder.entity_id == entity_id
            )
        )
    )
    for folder in folders:
        db.delete(folder)
    if folders:
        db.commit()
