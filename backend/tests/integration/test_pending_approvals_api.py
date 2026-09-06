"""The dashboard's "pending my approval" list -- surfaced via
GET /dashboard/summary's pending_approvals field, since there's no
dedicated endpoint. Covers one entity type per stage shape (CAIGO-only,
owner-then-CAIGO) rather than exhaustively repeating every entity type,
since pending_approvals_service applies the identical check per type.
"""

from fastapi.testclient import TestClient

from app.models.user import UserRole
from tests.integration.test_ai_system_lifecycle_api import LIFECYCLE, make_system, reach_validation
from tests.integration.test_risk_assessments_api import create_risk_assessment


def pending(client: TestClient) -> list[dict]:
    return client.get("/api/v1/dashboard/summary").json()["pending_approvals"]


def test_non_caigo_admin_sees_no_pending_approvals(
    client: TestClient, make_user, login_as
) -> None:
    policy = client.post("/api/v1/policies", json={"title": "Vendor Policy"}).json()
    client.post(f"/api/v1/policies/{policy['id']}/submit-for-review")

    login_as(make_user(role=UserRole.ADMIN))

    assert pending(client) == []


def test_caigo_sees_a_policy_awaiting_their_approval(
    client: TestClient, test_user, make_caigo, make_user, login_as
) -> None:
    policy = client.post("/api/v1/policies", json={"title": "Vendor Policy"}).json()
    client.post(f"/api/v1/policies/{policy['id']}/submit-for-review")

    caigo = make_user(role=UserRole.ADMIN)
    make_caigo(caigo)
    login_as(caigo)

    items = pending(client)
    assert len(items) == 1
    assert items[0]["entity_type"] == "Policy"
    assert items[0]["entity_id"] == policy["id"]
    assert items[0]["title"] == "Vendor Policy"


def test_caigo_does_not_see_their_own_submission(
    client: TestClient, test_user, make_caigo
) -> None:
    make_caigo(test_user)
    policy = client.post("/api/v1/policies", json={"title": "Vendor Policy"}).json()
    client.post(f"/api/v1/policies/{policy['id']}/submit-for-review")

    assert pending(client) == []


def test_ai_system_deployment_only_shown_once_requested(
    client: TestClient, test_user, caigo_admin, login_as
) -> None:
    row_id = make_system(client)
    reach_validation(client, row_id)
    client.put(
        LIFECYCLE.format(row_id=row_id) + "/deployment-record",
        json={
            "deployment_environment": "production",
            "deployment_version": "1.0",
            "deployed_at": "2026-09-01",
        },
    )

    login_as(caigo_admin)
    # Gate-eligible (record captured) but never actually requested yet.
    assert pending(client) == []

    # Someone else (not caigo_admin) requests approval.
    login_as(test_user)
    client.post(LIFECYCLE.format(row_id=row_id) + "/request-deployment-approval")

    login_as(caigo_admin)
    items = pending(client)
    assert len(items) == 1
    assert items[0]["entity_type"] == "AISystemDeployment"
    assert items[0]["entity_id"] == row_id


def test_ai_system_owner_sees_risk_assessment_pending_their_approval(
    client: TestClient, make_user, login_as
) -> None:
    created = create_risk_assessment(client)
    owner = make_user()
    client.put(
        f"/api/v1/ai-systems/{created['ai_system_row_id']}/lifecycle/owner",
        json={"owner_id": owner.id},
    )
    client.post(f"/api/v1/risk-assessments/{created['id']}/submit-for-owner-approval")

    login_as(owner)
    items = pending(client)

    assert len(items) == 1
    assert items[0]["entity_type"] == "RiskAssessment"
    assert items[0]["entity_id"] == created["id"]
    assert items[0]["stage_label"] == "Awaiting your approval as this AI system's owner"


def test_caigo_sees_risk_assessment_pending_final_approval(
    client: TestClient, make_user, login_as, caigo_admin
) -> None:
    created = create_risk_assessment(client)
    owner = make_user()
    client.put(
        f"/api/v1/ai-systems/{created['ai_system_row_id']}/lifecycle/owner",
        json={"owner_id": owner.id},
    )
    client.post(f"/api/v1/risk-assessments/{created['id']}/submit-for-owner-approval")
    login_as(owner)
    client.post(f"/api/v1/risk-assessments/{created['id']}/approve-owner-stage")

    login_as(caigo_admin)
    items = pending(client)

    assert len(items) == 1
    assert items[0]["entity_type"] == "RiskAssessment"
    assert items[0]["stage_label"] == "Awaiting your approval as Chief AI Governance Officer"
