from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.risk_assessment import RiskAssessment


def get(db: Session, risk_assessment_id: int) -> RiskAssessment | None:
    return db.get(RiskAssessment, risk_assessment_id)


def list_all(db: Session) -> list[RiskAssessment]:
    return list(db.scalars(select(RiskAssessment).order_by(RiskAssessment.id)))


def get_for_ai_system(db: Session, ai_system_row_id: int) -> RiskAssessment | None:
    """An AI system has at most one risk assessment."""
    return db.scalar(
        select(RiskAssessment).where(RiskAssessment.ai_system_row_id == ai_system_row_id)
    )


def create(db: Session, risk_assessment: RiskAssessment) -> RiskAssessment:
    db.add(risk_assessment)
    db.commit()
    db.refresh(risk_assessment)
    return risk_assessment


def save(db: Session, risk_assessment: RiskAssessment) -> RiskAssessment:
    db.commit()
    db.refresh(risk_assessment)
    return risk_assessment


def delete(db: Session, risk_assessment: RiskAssessment) -> None:
    db.delete(risk_assessment)
    db.commit()
