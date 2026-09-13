"""Records that point at other records must not be left pointing at nothing.

Three cases: a dataset whose AI system is deleted, a closed risk item whose
supporting evidence is deleted, and a document (or folder) whose owning
Policy, Procedure, AI system or impact assessment is deleted.
"""

import io
import os
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.core import risk_scoring
from app.repositories import evidence_repository, folder_repository, sheet_repository
from app.schemas.folder import FolderCreate
from app.schemas.impact_assessment import ImpactAssessmentCreate
from app.schemas.policy import PolicyCreate
from app.schemas.procedure import ProcedureCreate
from app.schemas.risk_assessment import RiskAssessmentCreate
from app.services import (
    ai_system_inventory_service,
    data_inventory_service,
    evidence_service,
    folder_service,
    impact_assessment_service,
    policy_service,
    procedure_service,
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


def upload_document(
    db: Session,
    entity_type: str,
    entity_id: int,
    folder_id: int | None = None,
    filename: str = "doc.pdf",
):
    return evidence_service.upload_evidence(
        db,
        entity_type,
        entity_id,
        folder_id,
        SimpleNamespace(
            filename=filename, content_type="application/pdf", file=io.BytesIO(b"x")
        ),
        "A document",
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


# ---------- a deleted record can't leave its documents behind ----------


def test_deleting_a_draft_policy_removes_its_documents_and_folders(
    db_session: Session,
) -> None:
    policy = policy_service.create_policy(
        db_session, PolicyCreate(title="Retention Policy"), actor_id=None
    )
    folder = folder_service.create_folder(
        db_session,
        FolderCreate(entity_type="Policy", entity_id=policy.id, name="Drafts"),
        actor_id=None,
    )
    flat = upload_document(db_session, "Policy", policy.id)
    foldered = upload_document(db_session, "Policy", policy.id, folder_id=folder.id)
    assert os.path.exists(flat.storage_path)
    assert os.path.exists(foldered.storage_path)

    policy_service.delete_policy(db_session, policy.id, actor_id=None)

    assert evidence_repository.list_for_entity(db_session, "Policy", policy.id) == []
    assert folder_repository.get(db_session, folder.id) is None
    assert not os.path.exists(flat.storage_path)
    assert not os.path.exists(foldered.storage_path)


def test_deleting_a_draft_procedure_removes_its_documents_and_folders(
    db_session: Session,
) -> None:
    procedure = procedure_service.create_procedure(
        db_session, ProcedureCreate(title="Incident Response"), actor_id=None
    )
    document = upload_document(db_session, "Procedure", procedure.id)

    procedure_service.delete_procedure(db_session, procedure.id, actor_id=None)

    assert evidence_repository.list_for_entity(db_session, "Procedure", procedure.id) == []
    assert not os.path.exists(document.storage_path)


def test_deleting_an_ai_system_removes_its_documents(db_session: Session) -> None:
    """Covers the stage-gate uploads (Design Document, Validation Report, ...)
    and anything else filed through the system's own document browser -- all
    tagged entity_type="AISystem", not this service's own ENTITY_TYPE (which
    names the inventory sheet, not one system)."""
    row_id = make_ai_system(db_session)
    document = upload_document(db_session, "AISystem", row_id)

    ai_system_inventory_service.delete_row(db_session, row_id, actor_id=None)

    assert evidence_repository.list_for_entity(db_session, "AISystem", row_id) == []
    assert not os.path.exists(document.storage_path)


def test_deleting_an_impact_assessment_removes_foldered_evidence_too(
    db_session: Session, make_user
) -> None:
    """evidence_service.delete_all_for_entity used to only look at the top
    folder level -- this is the case that was silently missed."""
    make_user()
    row_id = make_ai_system(db_session)
    assessment = impact_assessment_service.create_for_ai_system(
        db_session, row_id, ImpactAssessmentCreate(), actor_id=None
    )
    folder = folder_service.create_folder(
        db_session,
        FolderCreate(entity_type="ImpactAssessment", entity_id=assessment.id, name="Notes"),
        actor_id=None,
    )
    foldered = upload_document(
        db_session, "ImpactAssessment", assessment.id, folder_id=folder.id
    )

    impact_assessment_service.delete(db_session, assessment.id, actor_id=None)

    assert evidence_repository.list_for_entity(
        db_session, "ImpactAssessment", assessment.id
    ) == []
    assert folder_repository.get(db_session, folder.id) is None
    assert not os.path.exists(foldered.storage_path)
