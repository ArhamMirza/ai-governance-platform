"""One rule across the app: an approval describes the artifact as it stands,
so changing what was approved withdraws the approval and returns the record to
draft. Progress *against* an approved artifact -- treating and closing risk
items -- is not a change to it and leaves the sign-off standing.
"""

import io
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.impact_assessment import ImpactAssessmentStatus
from app.models.risk_assessment import RiskAssessmentStatus
from app.schemas.impact_assessment import ImpactAssessmentUpdate
from app.schemas.risk_assessment import RiskAssessmentCreate, RiskAssessmentUpdate
from app.schemas.sheet import ColumnDef
from app.services import (
    ai_system_inventory_service,
    evidence_service,
    impact_assessment_service,
    risk_assessment_service,
)
from tests.helpers import complete_impact_assessment_db


@pytest.fixture(autouse=True)
def _an_existing_user(make_user):
    """tests.helpers._ensure_owner assigns whichever user happens to exist as
    the AI System Owner, and submitting an assessment requires one. These
    tests work against db_session directly, so there's no client fixture
    standing a user up for them."""
    return make_user()


def make_ai_system(db: Session) -> int:
    return ai_system_inventory_service.add_row(
        db, {"name": "Resume Screener"}, actor_id=None
    ).id


def completed_risk_assessment(db: Session) -> int:
    """A risk assessment that has been all the way through owner and CAIGO
    sign-off, so the rule under test has something to withdraw."""
    ai_system_row_id = make_ai_system(db)
    complete_impact_assessment_db(db, ai_system_row_id)
    assessment = risk_assessment_service.create_risk_assessment(
        db, RiskAssessmentCreate(ai_system_row_id=ai_system_row_id), actor_id=None
    )
    risk_assessment_service.submit_for_owner_approval(db, assessment.id, actor_id=None)
    risk_assessment_service.approve_owner_stage(db, assessment.id, actor_id=None)
    risk_assessment_service.approve_caigo_stage(db, assessment.id, actor_id=None)
    return assessment.id


def status_of(db: Session, risk_assessment_id: int) -> str:
    return risk_assessment_service.get_risk_assessment(db, risk_assessment_id).status


def add_item(db: Session, risk_assessment_id: int, **data) -> int:
    payload = {"category": "Bias", "likelihood": 2, "impact": 2, "status": "open"}
    payload.update(data)
    return risk_assessment_service.add_row(
        db, risk_assessment_id, payload, actor_id=None
    ).id


# ---------- risk assessments ----------


def test_adding_a_risk_item_withdraws_the_approval(db_session: Session) -> None:
    assessment_id = completed_risk_assessment(db_session)

    add_item(db_session, assessment_id)

    assert status_of(db_session, assessment_id) == RiskAssessmentStatus.DRAFT


def test_the_withdrawal_clears_both_approvers(db_session: Session) -> None:
    assessment_id = completed_risk_assessment(db_session)

    add_item(db_session, assessment_id)

    assessment = risk_assessment_service.get_risk_assessment(db_session, assessment_id)
    assert assessment.owner_approved_by is None and assessment.owner_approved_at is None
    assert assessment.caigo_approved_by is None and assessment.caigo_approved_at is None


def test_rescoring_a_risk_item_withdraws_the_approval(db_session: Session) -> None:
    assessment_id = completed_risk_assessment(db_session)
    row_id = add_item(db_session, assessment_id)
    _recomplete(db_session, assessment_id)

    risk_assessment_service.update_row(
        db_session, assessment_id, row_id, {"likelihood": 5}, actor_id=None
    )

    assert status_of(db_session, assessment_id) == RiskAssessmentStatus.DRAFT


def test_treating_a_risk_item_leaves_the_approval_standing(db_session: Session) -> None:
    """Treatment is the work an approved assessment exists to drive -- it
    can't be the thing that invalidates the approval."""
    assessment_id = completed_risk_assessment(db_session)
    row_id = add_item(db_session, assessment_id)
    _recomplete(db_session, assessment_id)

    risk_assessment_service.update_row(
        db_session, assessment_id, row_id, {"status": "in_progress"}, actor_id=None
    )

    assert status_of(db_session, assessment_id) == RiskAssessmentStatus.COMPLETED


def test_closing_a_risk_item_leaves_the_approval_standing(db_session: Session) -> None:
    assessment_id = completed_risk_assessment(db_session)
    row_id = add_item(db_session, assessment_id)
    _recomplete(db_session, assessment_id)
    evidence_service.upload_evidence(
        db_session,
        "RiskItem",
        row_id,
        None,
        SimpleNamespace(
            filename="proof.pdf", content_type="application/pdf", file=io.BytesIO(b"x")
        ),
        "Mitigation proof",
        actor_id=None,
    )

    risk_assessment_service.close_risk_item(db_session, assessment_id, row_id, actor_id=None)

    assert status_of(db_session, assessment_id) == RiskAssessmentStatus.COMPLETED


def test_an_edit_that_changes_nothing_leaves_the_approval_standing(
    db_session: Session,
) -> None:
    assessment_id = completed_risk_assessment(db_session)
    row_id = add_item(db_session, assessment_id, category="Bias")
    _recomplete(db_session, assessment_id)

    risk_assessment_service.update_row(
        db_session, assessment_id, row_id, {"category": "Bias"}, actor_id=None
    )

    assert status_of(db_session, assessment_id) == RiskAssessmentStatus.COMPLETED


def test_deleting_a_risk_item_withdraws_the_approval(db_session: Session) -> None:
    assessment_id = completed_risk_assessment(db_session)
    row_id = add_item(db_session, assessment_id)
    _recomplete(db_session, assessment_id)

    risk_assessment_service.delete_row(db_session, assessment_id, row_id, actor_id=None)

    assert status_of(db_session, assessment_id) == RiskAssessmentStatus.DRAFT


def test_changing_the_columns_withdraws_the_approval(db_session: Session) -> None:
    assessment_id = completed_risk_assessment(db_session)

    risk_assessment_service.set_columns(
        db_session,
        assessment_id,
        [*risk_assessment_service.DEFAULT_COLUMNS, ColumnDef(key="note", label="Note")],
        actor_id=None,
    )

    assert status_of(db_session, assessment_id) == RiskAssessmentStatus.DRAFT


def test_re_uploading_the_sheet_withdraws_the_approval(db_session: Session) -> None:
    assessment_id = completed_risk_assessment(db_session)
    upload = SimpleNamespace(
        filename="risks.csv", file=io.BytesIO(b"Category,Likelihood\nBias,3\n")
    )

    risk_assessment_service.import_upload(db_session, assessment_id, upload, actor_id=None)

    assert status_of(db_session, assessment_id) == RiskAssessmentStatus.DRAFT


def test_changing_the_assessor_withdraws_the_approval(db_session: Session) -> None:
    assessment_id = completed_risk_assessment(db_session)

    risk_assessment_service.update_risk_assessment(
        db_session, assessment_id, RiskAssessmentUpdate(assessor_id=42), actor_id=None
    )

    assert status_of(db_session, assessment_id) == RiskAssessmentStatus.DRAFT


def _recomplete(db: Session, risk_assessment_id: int) -> None:
    """Walk an assessment that a test just knocked back to draft through the
    chain again, so the next action has a live approval to withdraw."""
    risk_assessment_service.submit_for_owner_approval(db, risk_assessment_id, actor_id=None)
    assessment = risk_assessment_service.get_risk_assessment(db, risk_assessment_id)
    if assessment.status == RiskAssessmentStatus.PENDING_OWNER_APPROVAL:
        risk_assessment_service.approve_owner_stage(db, risk_assessment_id, actor_id=None)
    risk_assessment_service.approve_caigo_stage(db, risk_assessment_id, actor_id=None)


# ---------- impact assessments ----------


def _factor(db: Session, assessment_id: int, name: str):
    factors = impact_assessment_service.get_factors(db, assessment_id)
    return next(f for f in factors if f.factor == name)


def test_rescoring_an_impact_factor_withdraws_the_approval(db_session: Session) -> None:
    ai_system_row_id = make_ai_system(db_session)
    assessment_id = complete_impact_assessment_db(db_session, ai_system_row_id)
    fairness = _factor(db_session, assessment_id, "Fairness")

    impact_assessment_service.update_factor(
        db_session, assessment_id, "Fairness",
        fairness.benefits, fairness.harms, fairness.criteria, fairness.score % 5 + 1,
        actor_id=None,
    )

    assessment = impact_assessment_service.get(db_session, assessment_id)
    assert assessment.status == ImpactAssessmentStatus.DRAFT
    assert assessment.caigo_approved_by is None


def test_an_impact_factor_edit_that_changes_nothing_leaves_the_approval(
    db_session: Session,
) -> None:
    ai_system_row_id = make_ai_system(db_session)
    assessment_id = complete_impact_assessment_db(db_session, ai_system_row_id)
    # Resending exactly what's already there -- a completed assessment has
    # every factor written up, so blanks here would be a real edit.
    fairness = _factor(db_session, assessment_id, "Fairness")

    impact_assessment_service.update_factor(
        db_session, assessment_id, "Fairness",
        fairness.benefits, fairness.harms, fairness.criteria, fairness.score,
        actor_id=None,
    )

    assessment = impact_assessment_service.get(db_session, assessment_id)
    assert assessment.status == ImpactAssessmentStatus.COMPLETED


def test_rewriting_the_impact_narrative_withdraws_the_approval(db_session: Session) -> None:
    ai_system_row_id = make_ai_system(db_session)
    assessment_id = complete_impact_assessment_db(db_session, ai_system_row_id)

    impact_assessment_service.update(
        db_session,
        assessment_id,
        ImpactAssessmentUpdate(system_description="Rewritten after sign-off."),
        actor_id=None,
    )

    assessment = impact_assessment_service.get(db_session, assessment_id)
    assert assessment.status == ImpactAssessmentStatus.DRAFT


def test_the_factor_scorecard_survives_a_withdrawal(db_session: Session) -> None:
    """Going back to draft withdraws the approval, not the work."""
    ai_system_row_id = make_ai_system(db_session)
    assessment_id = complete_impact_assessment_db(db_session, ai_system_row_id)

    impact_assessment_service.update_factor(
        db_session, assessment_id, "Fairness", "Benefits.", None, None, 3, actor_id=None
    )

    factors = impact_assessment_service.get_factors(db_session, assessment_id)
    fairness = next(f for f in factors if f.factor == "Fairness")
    assert fairness.score == 3 and fairness.benefits == "Benefits."


# ---------- ISO 42001 8.4 sequencing is maintained, not just enforced ----------


def test_cannot_delete_an_impact_assessment_a_risk_assessment_stands_on(
    db_session: Session,
) -> None:
    ai_system_row_id = make_ai_system(db_session)
    assessment_id = complete_impact_assessment_db(db_session, ai_system_row_id)
    risk_assessment_service.create_risk_assessment(
        db_session, RiskAssessmentCreate(ai_system_row_id=ai_system_row_id), actor_id=None
    )

    with pytest.raises(ConflictError):
        impact_assessment_service.delete(db_session, assessment_id, actor_id=None)


def test_deleting_the_risk_assessment_first_frees_the_impact_assessment(
    db_session: Session,
) -> None:
    ai_system_row_id = make_ai_system(db_session)
    assessment_id = complete_impact_assessment_db(db_session, ai_system_row_id)
    risk_assessment = risk_assessment_service.create_risk_assessment(
        db_session, RiskAssessmentCreate(ai_system_row_id=ai_system_row_id), actor_id=None
    )

    risk_assessment_service.delete_risk_assessment(
        db_session, risk_assessment.id, actor_id=None
    )
    impact_assessment_service.delete(db_session, assessment_id, actor_id=None)

    assert impact_assessment_service.get_for_ai_system(db_session, ai_system_row_id) is None


def test_deleting_the_ai_system_still_cascades_through_both(db_session: Session) -> None:
    """ai_system_inventory_service.delete_row deletes the risk assessment
    before the impact assessment -- if that order ever flips, the new guard
    turns deleting an AI system into a hard error."""
    ai_system_row_id = make_ai_system(db_session)
    complete_impact_assessment_db(db_session, ai_system_row_id)
    risk_assessment_service.create_risk_assessment(
        db_session, RiskAssessmentCreate(ai_system_row_id=ai_system_row_id), actor_id=None
    )

    ai_system_inventory_service.delete_row(db_session, ai_system_row_id, actor_id=None)

    assert impact_assessment_service.get_for_ai_system(db_session, ai_system_row_id) is None
    assert risk_assessment_service.get_for_ai_system(db_session, ai_system_row_id) is None
