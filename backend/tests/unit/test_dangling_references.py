"""Records that point at other records must not be left pointing at nothing.

Two cases: a dataset whose AI system is deleted, and a closed risk item whose
supporting evidence is deleted.
"""

import io
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.core import risk_scoring
from app.repositories import sheet_repository
from app.schemas.risk_assessment import RiskAssessmentCreate
from app.services import (
    ai_system_inventory_service,
    data_inventory_service,
    evidence_service,
    risk_assessment_service,
)
from tests.helpers import complete_impact_assessment_db


@pytest.fixture(autouse=True)
def _an_existing_user(make_user):
    """complete_impact_assessment_db assigns whichever user exists as the AI
    System Owner, and submitting needs one."""
    return make_user()


def make_ai_system(db: Session, name: str = "Resume Screener") -> int:
    return ai_system_inventory_service.add_row(db, {"name": name}, actor_id=None).id


def upload(db: Session, row_id: int, filename: str = "proof.pdf"):
    return evidence_service.upload_evidence(
        db,
        "RiskItem",
        row_id,
        None,
        SimpleNamespace(
            filename=filename, content_type="application/pdf", file=io.BytesIO(b"x")
        ),
        "Mitigation proof",
        actor_id=None,
    )


# ---------- a dataset outlives the system that used it ----------


def test_deleting_an_ai_system_unlinks_its_datasets_without_deleting_them(
    db_session: Session,
) -> None:
    ai_system_row_id = make_ai_system(db_session)
    dataset = data_inventory_service.add_row(
        db_session,
        {"dataset_name": "Applicant CVs", "ai_system_row_id": str(ai_system_row_id)},
        actor_id=None,
    )

    ai_system_inventory_service.delete_row(db_session, ai_system_row_id, actor_id=None)

    rows = data_inventory_service.list_rows(db_session)
    assert [row.id for row in rows] == [dataset.id]
    assert "ai_system_row_id" not in rows[0].data
    assert rows[0].data["dataset_name"] == "Applicant CVs"


def test_a_dataset_linked_to_another_system_is_untouched(db_session: Session) -> None:
    doomed = make_ai_system(db_session, "Doomed")
    survivor = make_ai_system(db_session, "Survivor")
    data_inventory_service.add_row(
        db_session,
        {"dataset_name": "Other CVs", "ai_system_row_id": str(survivor)},
        actor_id=None,
    )

    ai_system_inventory_service.delete_row(db_session, doomed, actor_id=None)

    row = data_inventory_service.list_rows(db_session)[0]
    assert row.data["ai_system_row_id"] == str(survivor)


def test_unlinking_leaves_the_datasets_approval_standing(db_session: Session, make_user) -> None:
    """The owner didn't revise their dataset -- a pointer to a deleted row is
    broken bookkeeping either way, so clearing it isn't a content change."""
    owner = make_user()
    ai_system_row_id = make_ai_system(db_session)
    dataset = data_inventory_service.add_row(
        db_session,
        {
            "dataset_name": "Applicant CVs",
            "ai_system_row_id": str(ai_system_row_id),
            "data_owner": str(owner.id),
        },
        actor_id=None,
    )
    data_inventory_service.submit_for_approval(db_session, dataset.id, actor_id=None)
    data_inventory_service.approve(db_session, dataset.id, actor_id=None)

    ai_system_inventory_service.delete_row(db_session, ai_system_row_id, actor_id=None)

    record = data_inventory_service.get_or_create_record(db_session, dataset.id)
    assert record.status == "approved"


# ---------- a closure can't outlive its proof ----------


def closed_risk_item(db: Session) -> tuple[int, int]:
    """A risk assessment with one closed, evidenced risk item."""
    ai_system_row_id = make_ai_system(db)
    complete_impact_assessment_db(db, ai_system_row_id)
    assessment = risk_assessment_service.create_risk_assessment(
        db, RiskAssessmentCreate(ai_system_row_id=ai_system_row_id), actor_id=None
    )
    row = risk_assessment_service.add_row(
        db, assessment.id, {"category": "Bias", "status": "open"}, actor_id=None
    )
    upload(db, row.id)
    risk_assessment_service.close_risk_item(db, assessment.id, row.id, actor_id=None)
    return assessment.id, row.id


def test_deleting_the_last_evidence_reopens_a_closed_risk_item(db_session: Session) -> None:
    assessment_id, row_id = closed_risk_item(db_session)
    evidence = evidence_service.list_evidence(db_session, "RiskItem", row_id, None)[0]

    evidence_service.delete_evidence(db_session, evidence.id, actor_id=None)

    row = sheet_repository.get_row(db_session, row_id)
    assert risk_scoring.is_treated(row.data.get("status")) is False
    assert "closed_at" not in row.data and "closed_by" not in row.data


def test_deleting_one_of_several_leaves_it_closed(db_session: Session) -> None:
    assessment_id, row_id = closed_risk_item(db_session)
    upload(db_session, row_id, filename="second-proof.pdf")
    first = evidence_service.list_evidence(db_session, "RiskItem", row_id, None)[0]

    evidence_service.delete_evidence(db_session, first.id, actor_id=None)

    row = sheet_repository.get_row(db_session, row_id)
    assert risk_scoring.is_treated(row.data.get("status")) is True


def test_reopening_does_not_withdraw_the_assessments_approval(db_session: Session) -> None:
    """Treatment is progress against an approved assessment, not a change to
    it -- reopening runs through the same carve-out closing does."""
    assessment_id, row_id = closed_risk_item(db_session)
    risk_assessment_service.submit_for_owner_approval(db_session, assessment_id, actor_id=None)
    risk_assessment_service.approve_owner_stage(db_session, assessment_id, actor_id=None)
    risk_assessment_service.approve_caigo_stage(db_session, assessment_id, actor_id=None)
    evidence = evidence_service.list_evidence(db_session, "RiskItem", row_id, None)[0]

    evidence_service.delete_evidence(db_session, evidence.id, actor_id=None)

    assessment = risk_assessment_service.get_risk_assessment(db_session, assessment_id)
    assert assessment.status == "completed"


def test_deleting_evidence_on_an_open_item_changes_nothing(db_session: Session) -> None:
    ai_system_row_id = make_ai_system(db_session)
    complete_impact_assessment_db(db_session, ai_system_row_id)
    assessment = risk_assessment_service.create_risk_assessment(
        db_session, RiskAssessmentCreate(ai_system_row_id=ai_system_row_id), actor_id=None
    )
    row = risk_assessment_service.add_row(
        db_session, assessment.id, {"category": "Bias", "status": "open"}, actor_id=None
    )
    evidence = upload(db_session, row.id)

    evidence_service.delete_evidence(db_session, evidence.id, actor_id=None)

    assert sheet_repository.get_row(db_session, row.id).data["status"] == "open"
