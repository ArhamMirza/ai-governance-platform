"""Shared test helpers.

Risk assessments require a completed impact assessment for the AI system
first (ISO 42001 sequences 8.4 before the risk work, and
risk_assessment_service enforces it), so most risk-assessment tests need to
satisfy that precondition before they can get to what they actually test.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import app
from app.models.user import User
from app.schemas.impact_assessment import ImpactAssessmentCreate
from app.services import (
    ai_system_lifecycle_service,
    data_inventory_service,
    impact_assessment_service,
)


def _db_for(client: TestClient) -> Session:
    """The db_session backing this TestClient's get_db override -- lets a
    plain helper function (not a fixture) reach the same session a test's
    `client` fixture is already using, without every call site needing to
    additionally request `db_session` just for this helper's sake."""
    return next(app.dependency_overrides[get_db]())


def _ensure_owner(db: Session, ai_system_row_id: int) -> None:
    """submit_for_owner_approval requires a real owner on the AI system
    (otherwise the owner stage could never be approved) -- stand one up if
    this system doesn't already have one, using whichever user happens to
    exist (these helpers only run inside a `client`-backed test, which
    always creates at least test_user first)."""
    lifecycle = ai_system_lifecycle_service.get_or_create(db, ai_system_row_id)
    if lifecycle.owner_id is None:
        first_user_id = db.query(User).order_by(User.id).first().id
        ai_system_lifecycle_service.set_owner(
            db, ai_system_row_id, owner_id=first_user_id, actor_id=None
        )


def add_approved_dataset(
    client: TestClient, ai_system_row_id: int, dataset_name: str = "CVs"
) -> int:
    """A Data Inventory entry that has been through its review -- what the AI
    system's development-stage gate now requires. Walks the review at the
    service layer with actor_id=None for the same reason
    complete_impact_assessment does: this helper has only one client to act
    as, and None is the established "no real actor, nothing to enforce" case
    for the Data Owner and CAIGO checks."""
    db = _db_for(client)
    row = data_inventory_service.add_row(
        db,
        {"dataset_name": dataset_name, "ai_system_row_id": str(ai_system_row_id)},
        actor_id=None,
    )
    # submit_for_approval insists on a real Data Owner, so nobody can submit a
    # dataset that has no one accountable for it.
    first_user_id = db.query(User).order_by(User.id).first().id
    data_inventory_service.update_row(
        db, row.id, {"data_owner": str(first_user_id)}, actor_id=None
    )
    data_inventory_service.submit_for_approval(db, row.id, actor_id=None)
    data_inventory_service.approve(db, row.id, actor_id=None)
    return row.id


def complete_impact_assessment(client: TestClient, ai_system_row_id: int) -> dict:
    """API-shaped: creates the assessment over the client, same as before.
    Completing it now means clearing owner and CAIGO approval rather than a
    single PUT, and both of those are checked against the *acting* user --
    since this helper has only one client to act as, it drops to the
    service layer with actor_id=None to walk the assessment through both
    stages, exactly like complete_impact_assessment_db already does. None
    is the same "no real actor, nothing to enforce" case
    audit_service.require_different_approver already treats specially."""
    db = _db_for(client)
    _ensure_owner(db, ai_system_row_id)

    created = client.post(
        "/api/v1/impact-assessments",
        json={"ai_system_row_id": ai_system_row_id},
    )
    assert created.status_code == 201, created.text
    body = created.json()

    impact_assessment_service.submit_for_owner_approval(db, body["id"], actor_id=None)
    impact_assessment_service.approve_owner_stage(db, body["id"], actor_id=None)
    impact_assessment_service.approve_caigo_stage(db, body["id"], actor_id=None)

    return client.get(f"/api/v1/impact-assessments/{body['id']}").json()


def complete_impact_assessment_db(db: Session, ai_system_row_id: int) -> int:
    """Service path, for tests that work against db_session directly."""
    _ensure_owner(db, ai_system_row_id)
    assessment = impact_assessment_service.create_for_ai_system(
        db, ai_system_row_id, ImpactAssessmentCreate(), actor_id=None
    )
    impact_assessment_service.submit_for_owner_approval(db, assessment.id, actor_id=None)
    impact_assessment_service.approve_owner_stage(db, assessment.id, actor_id=None)
    impact_assessment_service.approve_caigo_stage(db, assessment.id, actor_id=None)
    return assessment.id
