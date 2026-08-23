from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.risk_criteria import RiskCriteria


def get(db: Session) -> RiskCriteria | None:
    """The singleton criteria row, or None before one is stored."""
    return db.scalars(select(RiskCriteria).order_by(RiskCriteria.id)).first()


def create(db: Session, criteria: RiskCriteria) -> RiskCriteria:
    db.add(criteria)
    db.commit()
    db.refresh(criteria)
    return criteria


def save(db: Session, criteria: RiskCriteria) -> RiskCriteria:
    db.commit()
    db.refresh(criteria)
    return criteria
