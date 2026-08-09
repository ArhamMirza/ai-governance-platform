from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.policy import Policy


def get(db: Session, policy_id: int) -> Policy | None:
    return db.get(Policy, policy_id)


def list_all(db: Session) -> list[Policy]:
    return list(db.scalars(select(Policy).order_by(Policy.id)))


def create(db: Session, policy: Policy) -> Policy:
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def save(db: Session, policy: Policy) -> Policy:
    db.commit()
    db.refresh(policy)
    return policy


def delete(db: Session, policy: Policy) -> None:
    db.delete(policy)
    db.commit()
