from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.corrective_action import CorrectiveAction


def get(db: Session, corrective_action_id: int) -> CorrectiveAction | None:
    return db.get(CorrectiveAction, corrective_action_id)


def list_all(db: Session) -> list[CorrectiveAction]:
    return list(db.scalars(select(CorrectiveAction).order_by(CorrectiveAction.id)))


def list_for_source(db: Session, source_type: str, source_id: int) -> list[CorrectiveAction]:
    """Every corrective action raised from one source record -- e.g. every
    one raised from a given audit finding."""
    return list(
        db.scalars(
            select(CorrectiveAction)
            .where(
                CorrectiveAction.source_type == source_type,
                CorrectiveAction.source_id == source_id,
            )
            .order_by(CorrectiveAction.id)
        )
    )


def create(db: Session, corrective_action: CorrectiveAction) -> CorrectiveAction:
    db.add(corrective_action)
    db.commit()
    db.refresh(corrective_action)
    return corrective_action


def save(db: Session, corrective_action: CorrectiveAction) -> CorrectiveAction:
    db.commit()
    db.refresh(corrective_action)
    return corrective_action


def delete(db: Session, corrective_action: CorrectiveAction) -> None:
    db.delete(corrective_action)
    db.commit()
