from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_system_lifecycle import AISystemLifecycle


def get_for_ai_system(db: Session, ai_system_row_id: int) -> AISystemLifecycle | None:
    return db.scalar(
        select(AISystemLifecycle).where(
            AISystemLifecycle.ai_system_row_id == ai_system_row_id
        )
    )


def list_all(db: Session) -> list[AISystemLifecycle]:
    return list(db.scalars(select(AISystemLifecycle).order_by(AISystemLifecycle.id)))


def create(db: Session, lifecycle: AISystemLifecycle) -> AISystemLifecycle:
    db.add(lifecycle)
    db.commit()
    db.refresh(lifecycle)
    return lifecycle


def save(db: Session, lifecycle: AISystemLifecycle) -> AISystemLifecycle:
    db.commit()
    db.refresh(lifecycle)
    return lifecycle


def delete_for_ai_system(db: Session, ai_system_row_id: int) -> None:
    lifecycle = get_for_ai_system(db, ai_system_row_id)
    if lifecycle is not None:
        db.delete(lifecycle)
        db.commit()
