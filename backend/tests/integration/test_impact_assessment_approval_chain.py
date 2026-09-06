"""The two-stage approval chain: Implementation Team submits, the AI
system's owner approves (skipped if the owner is the one submitting), then
the Chief AI Governance Officer gives the final sign-off.
"""

from fastapi.testclient import TestClient

from app.models.user import User, UserRole
from tests.integration.test_impact_assessments_api import create_impact_assessment


def set_owner(client: TestClient, ai_system_row_id: int, owner_id: int | None) -> None:
    response = client.put(
        f"/api/v1/ai-systems/{ai_system_row_id}/lifecycle/owner", json={"owner_id": owner_id}
    )
    assert response.status_code == 200, response.text


def test_full_approval_chain_completes_and_stamps_review_dates(
    client: TestClient, make_user, login_as, caigo_admin
) -> None:
    created = create_impact_assessment(client)
    owner = make_user()
    set_owner(client, created["ai_system_row_id"], owner.id)

    submitted = client.post(
        f"/api/v1/impact-assessments/{created['id']}/submit-for-owner-approval"
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "pending_owner_approval"

    login_as(owner)
    owner_approved = client.post(
        f"/api/v1/impact-assessments/{created['id']}/approve-owner-stage"
    )
    assert owner_approved.status_code == 200, owner_approved.text
    body = owner_approved.json()
    assert body["status"] == "pending_caigo_approval"
    assert body["owner_approved_by"] == owner.id

    login_as(caigo_admin)
    completed = client.post(
        f"/api/v1/impact-assessments/{created['id']}/approve-caigo-stage"
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
    created = create_impact_assessment(client)
    set_owner(client, created["ai_system_row_id"], test_user.id)

    submitted = client.post(
        f"/api/v1/impact-assessments/{created['id']}/submit-for-owner-approval"
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "pending_caigo_approval"
    assert submitted.json()["owner_approved_by"] is None

    login_as(caigo_admin)
    completed = client.post(
        f"/api/v1/impact-assessments/{created['id']}/approve-caigo-stage"
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"


def test_only_the_owner_can_approve_the_owner_stage(
    client: TestClient, make_user, login_as
) -> None:
    created = create_impact_assessment(client)
    owner = make_user()
    set_owner(client, created["ai_system_row_id"], owner.id)
    client.post(f"/api/v1/impact-assessments/{created['id']}/submit-for-owner-approval")

    not_the_owner = make_user()
    login_as(not_the_owner)
    response = client.post(f"/api/v1/impact-assessments/{created['id']}/approve-owner-stage")

    assert response.status_code == 403


def test_non_caigo_admin_cannot_approve_the_caigo_stage(
    client: TestClient, make_user, login_as
) -> None:
    created = create_impact_assessment(client)
    owner = make_user()
    set_owner(client, created["ai_system_row_id"], owner.id)
    client.post(f"/api/v1/impact-assessments/{created['id']}/submit-for-owner-approval")

    login_as(owner)
    client.post(f"/api/v1/impact-assessments/{created['id']}/approve-owner-stage")

    non_caigo_admin = make_user(role=UserRole.ADMIN)
    login_as(non_caigo_admin)
    response = client.post(f"/api/v1/impact-assessments/{created['id']}/approve-caigo-stage")

    assert response.status_code == 403


def test_cannot_approve_owner_stage_out_of_order(client: TestClient) -> None:
    created = create_impact_assessment(client)

    response = client.post(f"/api/v1/impact-assessments/{created['id']}/approve-owner-stage")

    assert response.status_code == 409


def test_cannot_approve_caigo_stage_out_of_order(client: TestClient) -> None:
    created = create_impact_assessment(client)

    response = client.post(f"/api/v1/impact-assessments/{created['id']}/approve-caigo-stage")

    assert response.status_code == 409


def test_update_still_rejects_setting_completed_directly(client: TestClient) -> None:
    created = create_impact_assessment(client)

    response = client.put(
        f"/api/v1/impact-assessments/{created['id']}", json={"status": "completed"}
    )

    assert response.status_code == 400
