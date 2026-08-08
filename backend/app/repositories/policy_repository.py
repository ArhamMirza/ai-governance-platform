from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.policy import Policy, PolicyVersion


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


def add_version(db: Session, version: PolicyVersion) -> PolicyVersion:
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def list_versions(db: Session, policy_id: int) -> list[PolicyVersion]:
    return list(
        db.scalars(
            select(PolicyVersion)
            .where(PolicyVersion.policy_id == policy_id)
            .order_by(PolicyVersion.version_no)
        )
    )
