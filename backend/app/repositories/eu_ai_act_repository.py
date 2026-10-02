from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.eu_ai_act_applicability import EuAiActApplicability


def get(db: Session) -> EuAiActApplicability | None:
    """The singleton assessment row, or None before one is recorded."""
    return db.scalars(select(EuAiActApplicability).order_by(EuAiActApplicability.id)).first()


def create(db: Session, settings: EuAiActApplicability) -> EuAiActApplicability:
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def save(db: Session, settings: EuAiActApplicability) -> EuAiActApplicability:
    db.commit()
    db.refresh(settings)
    return settings
