from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.impact_assessment import ImpactAssessment


def get(db: Session, impact_assessment_id: int) -> ImpactAssessment | None:
    return db.get(ImpactAssessment, impact_assessment_id)


def list_for_ai_system(db: Session, ai_system_row_id: int) -> list[ImpactAssessment]:
    return list(
        db.scalars(
            select(ImpactAssessment)
            .where(ImpactAssessment.ai_system_row_id == ai_system_row_id)
            .order_by(ImpactAssessment.created_at)
        )
    )


def create(db: Session, impact_assessment: ImpactAssessment) -> ImpactAssessment:
    db.add(impact_assessment)
    db.commit()
    db.refresh(impact_assessment)
    return impact_assessment


def save(db: Session, impact_assessment: ImpactAssessment) -> ImpactAssessment:
    db.commit()
    db.refresh(impact_assessment)
    return impact_assessment


def delete(db: Session, impact_assessment: ImpactAssessment) -> None:
    db.delete(impact_assessment)
    db.commit()
