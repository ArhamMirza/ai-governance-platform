from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.impact_factors import IMPACT_FACTORS
from app.models.impact_factor_assessment import ImpactFactorAssessment


def create_all_factors(db: Session, impact_assessment_id: int) -> list[ImpactFactorAssessment]:
    """Seeds the fixed scorecard -- one blank row per ISO 42005 impact
    factor -- when an ImpactAssessment is created."""
    rows = [
        ImpactFactorAssessment(impact_assessment_id=impact_assessment_id, factor=factor)
        for factor in IMPACT_FACTORS
    ]
    db.add_all(rows)
    db.commit()
    return list_for_assessment(db, impact_assessment_id)


def list_for_assessment(db: Session, impact_assessment_id: int) -> list[ImpactFactorAssessment]:
    return list(
        db.scalars(
            select(ImpactFactorAssessment)
            .where(ImpactFactorAssessment.impact_assessment_id == impact_assessment_id)
            .order_by(ImpactFactorAssessment.id)
        )
    )


def get_by_assessment_and_factor(
    db: Session, impact_assessment_id: int, factor: str
) -> ImpactFactorAssessment | None:
    return db.scalar(
        select(ImpactFactorAssessment).where(
            ImpactFactorAssessment.impact_assessment_id == impact_assessment_id,
            ImpactFactorAssessment.factor == factor,
        )
    )


def save(db: Session, factor_assessment: ImpactFactorAssessment) -> ImpactFactorAssessment:
    db.commit()
    db.refresh(factor_assessment)
    return factor_assessment


def delete_for_assessment(db: Session, impact_assessment_id: int) -> None:
    for row in list_for_assessment(db, impact_assessment_id):
        db.delete(row)
    db.commit()
