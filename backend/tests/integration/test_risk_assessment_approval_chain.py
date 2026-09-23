"""The two-stage approval chain: Implementation Team submits, the AI
system's owner approves (skipped if the owner is the one submitting), then
the Chief AI Governance Officer gives the final sign-off.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.services import governance_role_service
from tests.integration.test_risk_assessments_api import (
    create_ai_system_row,
    create_risk_assessment,
)


def set_owner(client: TestClient, ai_system_row_id: int, owner_id: int | None) -> None:
    response = client.put(
        f"/api/v1/ai-systems/{ai_system_row_id}/lifecycle/owner", json={"owner_id": owner_id}
    )
    assert response.status_code == 200, response.text


def test_full_approval_chain_completes_and_stamps_review_dates(
    client: TestClient, make_user, login_as, caigo_admin
) -> None:
    created = create_risk_assessment(client)
    owner = make_user()
    set_owner(client, created["ai_system_row_id"], owner.id)

    submitted = client.post(
        f"/api/v1/risk-assessments/{created['id']}/submit-for-owner-approval"
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "pending_owner_approval"

    login_as(owner)
    owner_approved = client.post(
        f"/api/v1/risk-assessments/{created['id']}/approve-owner-stage"
    )
    assert owner_approved.status_code == 200, owner_approved.text
    body = owner_approved.json()
    assert body["status"] == "pending_caigo_approval"
    assert body["owner_approved_by"] == owner.id

    login_as(caigo_admin)
    completed = client.post(
        f"/api/v1/risk-assessments/{created['id']}/approve-caigo-stage"
    )
    assert completed.status_code == 200, completed.text
    body = completed.json()
    assert body["status"] == "completed"
    assert body["caigo_approved_by"] == caigo_admin.id
    assert body["assessment_date"] is not None
    assert body["next_review_date"] is not None


def test_owner_submitting_their_own_work_skips_the_owner_stage(
    client: TestClient, test_user: User, caigo_admin, login_as
) -> None:
    created = create_risk_assessment(client)
    set_owner(client, created["ai_system_row_id"], test_user.id)

    submitted = client.post(
        f"/api/v1/risk-assessments/{created['id']}/submit-for-owner-approval"
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "pending_caigo_approval"
    assert submitted.json()["owner_approved_by"] is None

    login_as(caigo_admin)
    completed = client.post(
        f"/api/v1/risk-assessments/{created['id']}/approve-caigo-stage"
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"


def test_only_the_owner_can_approve_the_owner_stage(
    client: TestClient, make_user, login_as
) -> None:
    created = create_risk_assessment(client)
    owner = make_user()
    set_owner(client, created["ai_system_row_id"], owner.id)
    client.post(f"/api/v1/risk-assessments/{created['id']}/submit-for-owner-approval")

    not_the_owner = make_user()
    login_as(not_the_owner)
    response = client.post(f"/api/v1/risk-assessments/{created['id']}/approve-owner-stage")

    assert response.status_code == 403


def test_non_caigo_admin_cannot_approve_the_caigo_stage(
    client: TestClient, make_user, login_as
) -> None:
    created = create_risk_assessment(client)
    owner = make_user()
    set_owner(client, created["ai_system_row_id"], owner.id)
    client.post(f"/api/v1/risk-assessments/{created['id']}/submit-for-owner-approval")

    login_as(owner)
    client.post(f"/api/v1/risk-assessments/{created['id']}/approve-owner-stage")

    non_caigo_admin = make_user(role=UserRole.ADMIN)
    login_as(non_caigo_admin)
    response = client.post(f"/api/v1/risk-assessments/{created['id']}/approve-caigo-stage")

    assert response.status_code == 403


def test_an_active_caigo_delegate_can_approve_the_caigo_stage(
    client: TestClient, db_session: Session, make_user, login_as
) -> None:
    created = create_risk_assessment(client)
    owner = make_user()
    set_owner(client, created["ai_system_row_id"], owner.id)
    client.post(f"/api/v1/risk-assessments/{created['id']}/submit-for-owner-approval")
    login_as(owner)
    client.post(f"/api/v1/risk-assessments/{created['id']}/approve-owner-stage")

    delegate = make_user(role=UserRole.ADMIN)
    governance_role_service.delegate_caigo(
        db_session, delegate.id, datetime.now(UTC) + timedelta(days=1), actor_id=None
    )
    login_as(delegate)
    response = client.post(f"/api/v1/risk-assessments/{created['id']}/approve-caigo-stage")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_the_owner_approver_cannot_also_approve_the_caigo_stage_themselves(
    client: TestClient, db_session: Session, make_user, login_as, make_caigo
) -> None:
    # A backup approver exists so approving the owner stage is allowed (see
    # test_cannot_approve_owner_stage_when_the_owner_is_the_only_possible_approver
    # for that guard on its own) -- this test is about the separate rule
    # that the owner still can't also approve the CAIGO stage themselves.
    created = create_risk_assessment(client)
    owner = make_user(role=UserRole.ADMIN)
    make_caigo(owner)
    delegate = make_user(role=UserRole.ADMIN)
    governance_role_service.delegate_caigo(
        db_session, delegate.id, datetime.now(UTC) + timedelta(days=1), actor_id=None
    )
    set_owner(client, created["ai_system_row_id"], owner.id)
    client.post(f"/api/v1/risk-assessments/{created['id']}/submit-for-owner-approval")

    login_as(owner)
    approved_owner_stage = client.post(
        f"/api/v1/risk-assessments/{created['id']}/approve-owner-stage"
    )
    assert approved_owner_stage.status_code == 200, approved_owner_stage.text
    response = client.post(f"/api/v1/risk-assessments/{created['id']}/approve-caigo-stage")

    assert response.status_code == 409
    assert "same user" in response.json()["detail"]


def test_cannot_approve_owner_stage_when_the_owner_is_the_only_possible_approver(
    client: TestClient, make_user, login_as, make_caigo
) -> None:
    """Approving the owner stage always generates the CAIGO stage's own
    submission, attributed to the owner -- if the owner is also the sole
    CAIGO with no backup approver, refuse the owner-stage approval itself
    rather than leave the record stuck in the stage after it."""
    created = create_risk_assessment(client)
    owner = make_user(role=UserRole.ADMIN)
    make_caigo(owner)
    set_owner(client, created["ai_system_row_id"], owner.id)
    client.post(f"/api/v1/risk-assessments/{created['id']}/submit-for-owner-approval")

    login_as(owner)
    response = client.post(f"/api/v1/risk-assessments/{created['id']}/approve-owner-stage")

    assert response.status_code == 400
    assert "backup approver" in response.json()["detail"]
    assert (
        client.get(f"/api/v1/risk-assessments/{created['id']}").json()["status"]
        == "pending_owner_approval"
    )


def test_cannot_submit_when_the_submitter_is_also_owner_and_the_only_possible_approver(
    client: TestClient, test_user: User, make_caigo
) -> None:
    """submit_for_owner_approval skips straight to the CAIGO stage when the
    owner is the one submitting -- if that owner is also the sole CAIGO with
    no backup approver, refuse the submission itself."""
    make_caigo(test_user)
    created = create_risk_assessment(client)
    set_owner(client, created["ai_system_row_id"], test_user.id)

    response = client.post(
        f"/api/v1/risk-assessments/{created['id']}/submit-for-owner-approval"
    )

    assert response.status_code == 400
    assert "backup approver" in response.json()["detail"]
    assert client.get(f"/api/v1/risk-assessments/{created['id']}").json()["status"] == "draft"


def test_cannot_approve_owner_stage_out_of_order(client: TestClient) -> None:
    created = create_risk_assessment(client)

    response = client.post(f"/api/v1/risk-assessments/{created['id']}/approve-owner-stage")

    assert response.status_code == 409


def test_cannot_approve_caigo_stage_out_of_order(client: TestClient) -> None:
    created = create_risk_assessment(client)

    response = client.post(f"/api/v1/risk-assessments/{created['id']}/approve-caigo-stage")

    assert response.status_code == 409


def test_update_still_rejects_setting_completed_directly(client: TestClient) -> None:
    created = create_risk_assessment(client)

    response = client.put(
        f"/api/v1/risk-assessments/{created['id']}", json={"status": "completed"}
    )

    assert response.status_code == 400


def test_cannot_revert_a_completed_assessment_via_plain_update(
    client: TestClient, make_user, login_as, caigo_admin
) -> None:
    """A plain PUT must not be able to undo a CAIGO-signed-off approval by
    moving status back to draft/in_progress -- only draft/in_progress may be
    set directly, and only while the record isn't already in the pipeline."""
    created = create_risk_assessment(client)
    owner = make_user()
    set_owner(client, created["ai_system_row_id"], owner.id)
    client.post(f"/api/v1/risk-assessments/{created['id']}/submit-for-owner-approval")
    login_as(owner)
    client.post(f"/api/v1/risk-assessments/{created['id']}/approve-owner-stage")
    login_as(caigo_admin)
    client.post(f"/api/v1/risk-assessments/{created['id']}/approve-caigo-stage")

    response = client.put(
        f"/api/v1/risk-assessments/{created['id']}", json={"status": "draft"}
    )

    assert response.status_code == 400
    assert client.get(f"/api/v1/risk-assessments/{created['id']}").json()["status"] == "completed"


def test_submitting_without_an_ai_system_owner_is_rejected(client: TestClient) -> None:
    """Submitting when nobody is set as the AI system's owner would otherwise
    put the assessment in pending_owner_approval with no one able to ever
    approve it -- reject the submission itself instead. Creating a risk
    assessment always completes an impact assessment first, which itself
    requires an owner -- so the owner is cleared afterward to reach the
    otherwise-unreachable ownerless state."""
    created = create_risk_assessment(client)
    set_owner(client, created["ai_system_row_id"], None)

    response = client.post(
        f"/api/v1/risk-assessments/{created['id']}/submit-for-owner-approval"
    )

    assert response.status_code == 400
    assert client.get(f"/api/v1/risk-assessments/{created['id']}").json()["status"] == "draft"


def test_impact_assessment_precondition_still_gates_risk_assessment_creation(
    client: TestClient,
) -> None:
    row = create_ai_system_row(client)

    response = client.post(
        "/api/v1/risk-assessments", json={"ai_system_row_id": row["id"]}
    )

    assert response.status_code == 400
