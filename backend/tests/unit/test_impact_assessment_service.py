import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.impact_factors import IMPACT_FACTORS
from app.core.review_cadence import next_review_date
from app.schemas.impact_assessment import ImpactAssessmentCreate, ImpactAssessmentUpdate
from app.schemas.risk_assessment import RiskAssessmentCreate
from app.services import (
    ai_system_inventory_service,
    ai_system_lifecycle_service,
    impact_assessment_service,
    risk_assessment_service,
)
from tests.helpers import fill_impact_assessment_db


def make_ai_system_row(db: Session) -> int:
    row = ai_system_inventory_service.add_row(db, {"name": "Resume Screener"}, actor_id=None)
    return row.id


def make_impact_assessment(db: Session, ai_system_row_id: int | None = None):
    if ai_system_row_id is None:
        ai_system_row_id = make_ai_system_row(db)
    return impact_assessment_service.create_for_ai_system(
        db, ai_system_row_id, ImpactAssessmentCreate(), actor_id=None
    )


def complete(db: Session, impact_assessment_id: int):
    assessment = impact_assessment_service.get(db, impact_assessment_id)
    ai_system_lifecycle_service.set_owner(
        db, assessment.ai_system_row_id, owner_id=1, actor_id=None
    )
    fill_impact_assessment_db(db, impact_assessment_id)
    impact_assessment_service.submit_for_owner_approval(db, impact_assessment_id, actor_id=None)
    impact_assessment_service.approve_owner_stage(db, impact_assessment_id, actor_id=None)
    return impact_assessment_service.approve_caigo_stage(
        db, impact_assessment_id, actor_id=None
    )


def test_create_for_ai_system_seeds_all_impact_factors(db_session: Session) -> None:
    created = make_impact_assessment(db_session)

    factors = impact_assessment_service.get_factors(db_session, created.id)
    assert sorted(f.factor for f in factors) == sorted(IMPACT_FACTORS)
    assert all(f.score is None and f.benefits is None for f in factors)


def test_create_rejects_an_ai_system_that_does_not_exist(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        impact_assessment_service.create_for_ai_system(
            db_session, 999999, ImpactAssessmentCreate(), actor_id=None
        )


def test_only_one_impact_assessment_per_ai_system(db_session: Session) -> None:
    """Re-assessing revisits this record; it does not add a second one."""
    ai_system_row_id = make_ai_system_row(db_session)
    make_impact_assessment(db_session, ai_system_row_id)

    with pytest.raises(ConflictError):
        make_impact_assessment(db_session, ai_system_row_id)


def test_impact_assessments_are_scoped_to_the_ai_system(db_session: Session) -> None:
    ai_system_row_id = make_ai_system_row(db_session)
    other_row_id = ai_system_inventory_service.add_row(
        db_session, {"name": "Other System"}, actor_id=None
    ).id
    make_impact_assessment(db_session, ai_system_row_id)
    make_impact_assessment(db_session, other_row_id)

    assert len(impact_assessment_service.list_for_ai_system(db_session, ai_system_row_id)) == 1
    assert (
        impact_assessment_service.get_for_ai_system(db_session, other_row_id).ai_system_row_id
        == other_row_id
    )


def test_risk_assessment_resolves_to_its_systems_impact_assessment(db_session: Session) -> None:
    ai_system_row_id = make_ai_system_row(db_session)
    impact = make_impact_assessment(db_session, ai_system_row_id)
    complete(db_session, impact.id)
    risk_assessment = risk_assessment_service.create_risk_assessment(
        db_session, RiskAssessmentCreate(ai_system_row_id=ai_system_row_id), actor_id=None
    )

    found = impact_assessment_service.list_for_risk_assessment(db_session, risk_assessment.id)

    assert [a.id for a in found] == [impact.id]


def test_update_narrative_fields(db_session: Session) -> None:
    created = make_impact_assessment(db_session)

    updated = impact_assessment_service.update(
        db_session,
        created.id,
        ImpactAssessmentUpdate(system_description="Screens resumes."),
        actor_id=None,
    )

    assert updated.system_description == "Screens resumes."


def test_completing_stamps_the_assessment_and_next_review_dates(db_session: Session) -> None:
    """Completion sets the yearly review cadence rather than leaving it unset."""
    created = make_impact_assessment(db_session)
    assert created.assessment_date is None and created.next_review_date is None

    completed = complete(db_session, created.id)

    assert completed.assessment_date is not None
    assert completed.next_review_date == next_review_date(completed.assessment_date)


def test_has_completed_for_ai_system_ignores_drafts(db_session: Session) -> None:
    ai_system_row_id = make_ai_system_row(db_session)
    created = make_impact_assessment(db_session, ai_system_row_id)

    assert not impact_assessment_service.has_completed_for_ai_system(
        db_session, ai_system_row_id
    )

    complete(db_session, created.id)

    assert impact_assessment_service.has_completed_for_ai_system(db_session, ai_system_row_id)


def test_update_factor_sets_benefits_harms_criteria_and_score(db_session: Session) -> None:
    created = make_impact_assessment(db_session)

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
    created = make_impact_assessment(db_session)

    with pytest.raises(ValidationError):
        impact_assessment_service.update_factor(
            db_session, created.id, "Safety", None, None, None, score, actor_id=None
        )


def test_update_factor_rejects_unknown_factor(db_session: Session) -> None:
    created = make_impact_assessment(db_session)

    with pytest.raises(ValidationError):
        impact_assessment_service.update_factor(
            db_session, created.id, "NotARealFactor", None, None, None, None, actor_id=None
        )


def test_delete_removes_assessment_and_factors(db_session: Session) -> None:
    created = make_impact_assessment(db_session)

    impact_assessment_service.delete(db_session, created.id, actor_id=None)

    with pytest.raises(NotFoundError):
        impact_assessment_service.get(db_session, created.id)
    assert impact_assessment_service.get_factors(db_session, created.id) == []


# ---------- nothing enters the approval pipeline half-written ----------


def ready_to_submit(db: Session):
    """A draft with everything missing_content asks for, and an owner who
    isn't the (None) submitter, so a submission lands in owner approval."""
    created = make_impact_assessment(db)
    ai_system_lifecycle_service.set_owner(
        db, created.ai_system_row_id, owner_id=1, actor_id=None
    )
    fill_impact_assessment_db(db, created.id)
    return created


def factor_row(db: Session, impact_assessment_id: int, factor: str):
    return next(
        f
        for f in impact_assessment_service.get_factors(db, impact_assessment_id)
        if f.factor == factor
    )


def refusal(db: Session, impact_assessment_id: int) -> str:
    with pytest.raises(ValidationError) as excinfo:
        impact_assessment_service.submit_for_owner_approval(
            db, impact_assessment_id, actor_id=None
        )
    assert impact_assessment_service.get(db, impact_assessment_id).status == "draft"
    return str(excinfo.value)


def test_an_empty_assessment_cannot_be_submitted(db_session: Session) -> None:
    created = make_impact_assessment(db_session)
    ai_system_lifecycle_service.set_owner(
        db_session, created.ai_system_row_id, owner_id=1, actor_id=None
    )

    assert refusal(db_session, created.id) == (
        "Can't submit: System Description, Intended Purpose, Foreseeable Misuse, "
        "Data & Model Information, Deployment Environment, Affected Interested Parties, "
        "Role of Human Oversight and Conclusion are empty, all 8 factors are unscored, "
        "all 8 factors have no benefits written and all 8 factors have no harms written."
    )


def test_a_complete_assessment_is_submitted(db_session: Session) -> None:
    created = ready_to_submit(db_session)

    submitted = impact_assessment_service.submit_for_owner_approval(
        db_session, created.id, actor_id=None
    )

    assert submitted.status == "pending_owner_approval"
    # Scoring criteria explain the scale rather than this system's impact,
    # so they aren't part of what's required.
    assert all(
        f.criteria is None for f in impact_assessment_service.get_factors(db_session, created.id)
    )


def test_refusal_names_the_empty_sections_and_unscored_factors(db_session: Session) -> None:
    created = ready_to_submit(db_session)
    impact_assessment_service.update(
        db_session, created.id, ImpactAssessmentUpdate(conclusion=""), actor_id=None
    )
    for factor in ("Privacy", "Safety", "Fairness"):
        row = factor_row(db_session, created.id, factor)
        impact_assessment_service.update_factor(
            db_session, created.id, factor, row.benefits, row.harms, row.criteria, None,
            actor_id=None,
        )

    assert refusal(db_session, created.id) == (
        "Can't submit: Conclusion is empty and 3 factors are unscored "
        "(Fairness, Privacy, Safety)."
    )


def test_a_whitespace_only_section_counts_as_empty(db_session: Session) -> None:
    created = ready_to_submit(db_session)
    impact_assessment_service.update(
        db_session, created.id, ImpactAssessmentUpdate(intended_purpose="   \n"), actor_id=None
    )

    assert refusal(db_session, created.id) == "Can't submit: Intended Purpose is empty."


def test_a_factor_without_benefits_is_refused(db_session: Session) -> None:
    created = ready_to_submit(db_session)
    row = factor_row(db_session, created.id, "Privacy")
    impact_assessment_service.update_factor(
        db_session, created.id, "Privacy", None, row.harms, row.criteria, row.score,
        actor_id=None,
    )

    assert refusal(db_session, created.id) == (
        "Can't submit: 1 factor has no benefits written (Privacy)."
    )


def test_a_factor_without_harms_is_refused(db_session: Session) -> None:
    created = ready_to_submit(db_session)
    row = factor_row(db_session, created.id, "Safety")
    impact_assessment_service.update_factor(
        db_session, created.id, "Safety", row.benefits, "  ", row.criteria, row.score,
        actor_id=None,
    )

    assert refusal(db_session, created.id) == (
        "Can't submit: 1 factor has no harms written (Safety)."
    )


def test_a_score_outside_the_scale_counts_as_unscored(db_session: Session) -> None:
    """update_factor refuses these, but a row written before that check (or
    straight into the database) mustn't pass as scored."""
    created = ready_to_submit(db_session)
    row = factor_row(db_session, created.id, "Reliability")
    row.score = 0
    db_session.commit()

    assert refusal(db_session, created.id) == (
        "Can't submit: 1 factor is unscored (Reliability)."
    )


@pytest.mark.parametrize(
    ("stage", "approve"),
    [
        ("pending_owner_approval", impact_assessment_service.approve_owner_stage),
        ("pending_caigo_approval", impact_assessment_service.approve_caigo_stage),
    ],
)
def test_an_empty_assessment_already_in_the_pipeline_cannot_be_approved(
    db_session: Session, stage: str, approve
) -> None:
    """One submitted before completeness was checked is already pending --
    signing it off would complete it empty, so each approval re-checks. Its
    status is left exactly where it was, not pushed back to draft."""
    created = make_impact_assessment(db_session)
    ai_system_lifecycle_service.set_owner(
        db_session, created.ai_system_row_id, owner_id=1, actor_id=None
    )
    created.status = stage
    db_session.commit()

    with pytest.raises(ValidationError, match=r"^Can't approve: .*are empty"):
        approve(db_session, created.id, actor_id=None)

    assert impact_assessment_service.get(db_session, created.id).status == stage
