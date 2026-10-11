from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.management_system_change import ChangeAISystem, ManagementSystemChange


def get(db: Session, change_id: int) -> ManagementSystemChange | None:
    return db.get(ManagementSystemChange, change_id)


def list_all(db: Session) -> list[ManagementSystemChange]:
    return list(
        db.scalars(
            select(ManagementSystemChange).order_by(
                ManagementSystemChange.planned_date, ManagementSystemChange.id
            )
        )
    )


def create(db: Session, change: ManagementSystemChange) -> ManagementSystemChange:
    db.add(change)
    db.commit()
    db.refresh(change)
    return change


def save(db: Session, change: ManagementSystemChange) -> ManagementSystemChange:
    db.commit()
    db.refresh(change)
    return change


def delete(db: Session, change: ManagementSystemChange) -> None:
    db.delete(change)
    db.commit()


def list_links(db: Session) -> list[ChangeAISystem]:
    return list(db.scalars(select(ChangeAISystem).order_by(ChangeAISystem.id)))


def list_links_for_change(db: Session, change_id: int) -> list[ChangeAISystem]:
    return list(
        db.scalars(
            select(ChangeAISystem)
            .where(ChangeAISystem.change_id == change_id)
            .order_by(ChangeAISystem.ai_system_row_id)
        )
    )


def list_links_for_ai_system(db: Session, ai_system_row_id: int) -> list[ChangeAISystem]:
    return list(
        db.scalars(
            select(ChangeAISystem)
            .where(ChangeAISystem.ai_system_row_id == ai_system_row_id)
            .order_by(ChangeAISystem.change_id)
        )
    )


def replace_links(db: Session, change_id: int, ai_system_row_ids: list[int]) -> None:
    """Makes the change's links exactly this set, in one commit, keeping the
    ones that survive rather than deleting and recreating them."""
    wanted = set(ai_system_row_ids)
    existing = {link.ai_system_row_id: link for link in list_links_for_change(db, change_id)}
    for row_id, link in existing.items():
        if row_id not in wanted:
            db.delete(link)
    for row_id in sorted(wanted - existing.keys()):
        db.add(ChangeAISystem(change_id=change_id, ai_system_row_id=row_id))
    db.commit()


def delete_links(db: Session, links: list[ChangeAISystem]) -> None:
    for link in links:
        db.delete(link)
    db.commit()
