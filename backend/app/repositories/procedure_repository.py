from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.procedure import Procedure


def get(db: Session, procedure_id: int) -> Procedure | None:
    return db.get(Procedure, procedure_id)


def list_all(db: Session) -> list[Procedure]:
    return list(db.scalars(select(Procedure).order_by(Procedure.id)))


def create(db: Session, procedure: Procedure) -> Procedure:
    db.add(procedure)
    db.commit()
    db.refresh(procedure)
    return procedure


def save(db: Session, procedure: Procedure) -> Procedure:
    db.commit()
    db.refresh(procedure)
    return procedure


def delete(db: Session, procedure: Procedure) -> None:
    db.delete(procedure)
    db.commit()
