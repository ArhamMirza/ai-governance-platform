from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.improvement import Improvement


def get(db: Session, improvement_id: int) -> Improvement | None:
    return db.get(Improvement, improvement_id)


def list_all(db: Session) -> list[Improvement]:
    return list(db.scalars(select(Improvement).order_by(Improvement.target_date, Improvement.id)))


def list_for_source(db: Session, source_type: str, source_id: int) -> list[Improvement]:
    return list(
        db.scalars(
            select(Improvement)
            .where(Improvement.source_type == source_type, Improvement.source_id == source_id)
            .order_by(Improvement.id)
        )
    )


def list_for_change(db: Session, change_id: int) -> list[Improvement]:
    return list(
        db.scalars(
            select(Improvement).where(Improvement.change_id == change_id).order_by(Improvement.id)
        )
    )


def create(db: Session, improvement: Improvement) -> Improvement:
    db.add(improvement)
    db.commit()
    db.refresh(improvement)
    return improvement


def save(db: Session, improvement: Improvement) -> Improvement:
    db.commit()
    db.refresh(improvement)
    return improvement


def delete(db: Session, improvement: Improvement) -> None:
    db.delete(improvement)
    db.commit()
