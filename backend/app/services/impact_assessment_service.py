"""AI system impact assessments (ISO 42001 clause 8.4 / Annex A.5, structured
per ISO/IEC 42005). Each assessment is scoped to one AI system
(ai_system_row_id, same sheet_rows FK RiskAssessment uses) rather than to a
single Risk Assessment run -- a system can be re-assessed several times, and
every Risk Assessment for that system shares the same impact history.

Each assessment carries a fixed scorecard of the eight ISO 42005 impact
factors -- benefits/harms/criteria written up by a human, score assigned
manually for now (a future pass can derive it automatically from the
benefits/harms/criteria text instead)."""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.impact_factors import IMPACT_FACTORS
from app.models.impact_assessment import ImpactAssessment
from app.models.impact_factor_assessment import ImpactFactorAssessment
from app.repositories import (
    impact_assessment_repository,
    impact_factor_assessment_repository,
    risk_assessment_repository,
    sheet_repository,
)
from app.schemas.impact_assessment import ImpactAssessmentCreate, ImpactAssessmentUpdate
from app.services import (
    ai_system_inventory_service,
    audit_service,
    evidence_service,
    framework_service,
)

ENTITY_TYPE = "ImpactAssessment"

MIN_SCORE = 1
MAX_SCORE = 5


def _get_or_raise(db: Session, impact_assessment_id: int) -> ImpactAssessment:
    impact_assessment = impact_assessment_repository.get(db, impact_assessment_id)
    if impact_assessment is None:
        raise NotFoundError("ImpactAssessment", impact_assessment_id)
    return impact_assessment


def _validate_ai_system_row(db: Session, ai_system_row_id: int) -> None:
    inventory_sheet = ai_system_inventory_service.get_or_create_sheet(db)
    row = sheet_repository.get_row(db, ai_system_row_id)
    if row is None or row.sheet_id != inventory_sheet.id:
        raise NotFoundError("AISystemRow", ai_system_row_id)


def list_for_ai_system(db: Session, ai_system_row_id: int) -> list[ImpactAssessment]:
    return impact_assessment_repository.list_for_ai_system(db, ai_system_row_id)


def list_for_risk_assessment(db: Session, risk_assessment_id: int) -> list[ImpactAssessment]:
    """Convenience for the risk-assessment detail page: resolves the risk
    assessment's AI system and returns every impact assessment scoped to it
    (not just ones created "through" this particular risk assessment)."""
    risk_assessment = risk_assessment_repository.get(db, risk_assessment_id)
    if risk_assessment is None:
        raise NotFoundError("RiskAssessment", risk_assessment_id)
    return list_for_ai_system(db, risk_assessment.ai_system_row_id)


def get(db: Session, impact_assessment_id: int) -> ImpactAssessment:
    return _get_or_raise(db, impact_assessment_id)


def get_factors(db: Session, impact_assessment_id: int) -> list[ImpactFactorAssessment]:
    return impact_factor_assessment_repository.list_for_assessment(db, impact_assessment_id)


def create_for_risk_assessment(
    db: Session, risk_assessment_id: int, data: ImpactAssessmentCreate, actor_id: int | None
) -> ImpactAssessment:
    """Entry point used by the risk-assessment detail page's "New Impact
    Assessment" action -- resolves to the underlying AI system."""
    risk_assessment = risk_assessment_repository.get(db, risk_assessment_id)
    if risk_assessment is None:
        raise NotFoundError("RiskAssessment", risk_assessment_id)
    return create_for_ai_system(db, risk_assessment.ai_system_row_id, data, actor_id)


def create_for_ai_system(
    db: Session, ai_system_row_id: int, data: ImpactAssessmentCreate, actor_id: int | None
) -> ImpactAssessment:
    _validate_ai_system_row(db, ai_system_row_id)

    impact_assessment = ImpactAssessment(
        ai_system_row_id=ai_system_row_id,
        assessor_id=data.assessor_id,
        assessment_date=data.assessment_date,
    )
    impact_assessment = impact_assessment_repository.create(db, impact_assessment)
    impact_factor_assessment_repository.create_all_factors(db, impact_assessment.id)
    audit_service.log(
        db, ENTITY_TYPE, impact_assessment.id, "created", actor_id,
        {"ai_system_row_id": ai_system_row_id},
    )
    return impact_assessment


def update(
    db: Session, impact_assessment_id: int, data: ImpactAssessmentUpdate, actor_id: int | None
) -> ImpactAssessment:
    impact_assessment = _get_or_raise(db, impact_assessment_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(impact_assessment, field, value)
    impact_assessment = impact_assessment_repository.save(db, impact_assessment)
    audit_service.log(db, ENTITY_TYPE, impact_assessment_id, "updated", actor_id, changes)
    return impact_assessment


def update_factor(
    db: Session,
    impact_assessment_id: int,
    factor: str,
    benefits: str | None,
    harms: str | None,
    criteria: str | None,
    score: int | None,
    actor_id: int | None,
) -> ImpactFactorAssessment:
    if factor not in IMPACT_FACTORS:
        raise ValidationError(f"Unknown impact factor: {factor}")
    if score is not None and not (MIN_SCORE <= score <= MAX_SCORE):
        raise ValidationError(f"Score must be between {MIN_SCORE} and {MAX_SCORE}")
    _get_or_raise(db, impact_assessment_id)

    factor_assessment = impact_factor_assessment_repository.get_by_assessment_and_factor(
        db, impact_assessment_id, factor
    )
    if factor_assessment is None:
        raise NotFoundError("ImpactFactorAssessment", impact_assessment_id)

    factor_assessment.benefits = benefits
    factor_assessment.harms = harms
    factor_assessment.criteria = criteria
    factor_assessment.score = score
    factor_assessment = impact_factor_assessment_repository.save(db, factor_assessment)
    audit_service.log(
        db, ENTITY_TYPE, impact_assessment_id, "factor_updated", actor_id,
        {"factor": factor, "score": score},
    )
    return factor_assessment


def delete(db: Session, impact_assessment_id: int, actor_id: int | None) -> None:
    impact_assessment = _get_or_raise(db, impact_assessment_id)
    impact_factor_assessment_repository.delete_for_assessment(db, impact_assessment_id)
    evidence_service.delete_all_for_entity(db, ENTITY_TYPE, impact_assessment_id)
    framework_service.delete_tags(db, ENTITY_TYPE, impact_assessment_id)
    impact_assessment_repository.delete(db, impact_assessment)
    audit_service.log(db, ENTITY_TYPE, impact_assessment_id, "deleted", actor_id)
