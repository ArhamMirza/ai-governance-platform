import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.impact_factors import IMPACT_FACTORS
from app.schemas.impact_assessment import ImpactAssessmentCreate, ImpactAssessmentUpdate
from app.schemas.risk_assessment import RiskAssessmentCreate
from app.services import (
    ai_system_inventory_service,
    impact_assessment_service,
    risk_assessment_service,
)


def make_ai_system_row(db: Session) -> int:
    row = ai_system_inventory_service.add_row(db, {"name": "Resume Screener"}, actor_id=None)
    return row.id


def make_risk_assessment(db: Session, ai_system_row_id: int | None = None) -> int:
    if ai_system_row_id is None:
        ai_system_row_id = make_ai_system_row(db)
    ra = risk_assessment_service.create_risk_assessment(
        db, RiskAssessmentCreate(ai_system_row_id=ai_system_row_id), actor_id=None
    )
    return ra.id


def test_create_for_risk_assessment_seeds_all_impact_factors(db_session: Session) -> None:
    ra_id = make_risk_assessment(db_session)

    created = impact_assessment_service.create_for_risk_assessment(
        db_session, ra_id, ImpactAssessmentCreate(), actor_id=None
    )

    factors = impact_assessment_service.get_factors(db_session, created.id)
    assert sorted(f.factor for f in factors) == sorted(IMPACT_FACTORS)
    assert all(f.score is None and f.benefits is None for f in factors)


def test_create_rejects_unknown_risk_assessment(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        impact_assessment_service.create_for_risk_assessment(
            db_session, 999999, ImpactAssessmentCreate(), actor_id=None
        )


def test_impact_assessments_are_scoped_to_the_ai_system_not_one_risk_assessment(
    db_session: Session,
) -> None:
    ai_system_row_id = make_ai_system_row(db_session)
    first_ra = make_risk_assessment(db_session, ai_system_row_id)
    second_ra = make_risk_assessment(db_session, ai_system_row_id)

    impact_assessment_service.create_for_risk_assessment(
        db_session, first_ra, ImpactAssessmentCreate(), actor_id=None
    )

    assert len(impact_assessment_service.list_for_risk_assessment(db_session, second_ra)) == 1


def test_update_narrative_fields(db_session: Session) -> None:
    ra_id = make_risk_assessment(db_session)
    created = impact_assessment_service.create_for_risk_assessment(
        db_session, ra_id, ImpactAssessmentCreate(), actor_id=None
    )

    updated = impact_assessment_service.update(
        db_session,
        created.id,
        ImpactAssessmentUpdate(system_description="Screens resumes."),
        actor_id=None,
    )

    assert updated.system_description == "Screens resumes."


def test_update_factor_sets_benefits_harms_criteria_and_score(db_session: Session) -> None:
    ra_id = make_risk_assessment(db_session)
    created = impact_assessment_service.create_for_risk_assessment(
        db_session, ra_id, ImpactAssessmentCreate(), actor_id=None
    )

    result = impact_assessment_service.update_factor(
        db_session,
        created.id,
        "Fairness",
        benefits="Standardized criteria.",
        harms="Potential encoded bias.",
        criteria="Score 4-5 if no disparate impact found.",
        score=3,
        actor_id=None,
    )

    assert result.score == 3
    assert result.benefits == "Standardized criteria."


@pytest.mark.parametrize("score", [0, 6, -1])
def test_update_factor_rejects_out_of_range_score(db_session: Session, score: int) -> None:
    ra_id = make_risk_assessment(db_session)
    created = impact_assessment_service.create_for_risk_assessment(
        db_session, ra_id, ImpactAssessmentCreate(), actor_id=None
    )

    with pytest.raises(ValidationError):
        impact_assessment_service.update_factor(
            db_session, created.id, "Safety", None, None, None, score, actor_id=None
        )


def test_update_factor_rejects_unknown_factor(db_session: Session) -> None:
    ra_id = make_risk_assessment(db_session)
    created = impact_assessment_service.create_for_risk_assessment(
        db_session, ra_id, ImpactAssessmentCreate(), actor_id=None
    )

    with pytest.raises(ValidationError):
        impact_assessment_service.update_factor(
            db_session, created.id, "NotARealFactor", None, None, None, None, actor_id=None
        )


def test_delete_removes_assessment_and_factors(db_session: Session) -> None:
    ra_id = make_risk_assessment(db_session)
    created = impact_assessment_service.create_for_risk_assessment(
        db_session, ra_id, ImpactAssessmentCreate(), actor_id=None
    )

    impact_assessment_service.delete(db_session, created.id, actor_id=None)

    with pytest.raises(NotFoundError):
        impact_assessment_service.get(db_session, created.id)
    assert impact_assessment_service.get_factors(db_session, created.id) == []
