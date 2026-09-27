from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.corrective_action import CorrectiveAction


def get(db: Session, corrective_action_id: int) -> CorrectiveAction | None:
    return db.get(CorrectiveAction, corrective_action_id)


def list_all(db: Session) -> list[CorrectiveAction]:
    return list(db.scalars(select(CorrectiveAction).order_by(CorrectiveAction.id)))


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
