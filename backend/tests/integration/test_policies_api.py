from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.services import governance_role_service


def create_policy(client: TestClient, **overrides) -> dict:
    payload = {"title": "Data Retention Policy"}
    payload.update(overrides)
    response = client.post("/api/v1/policies", json=payload)
    assert response.status_code == 201
    return response.json()


def upload_document(client: TestClient, policy_id: int, filename: str = "policy.pdf") -> dict:
    response = client.post(
        "/api/v1/evidence",
        data={"entity_type": "Policy", "entity_id": str(policy_id)},
        files={"file": (filename, b"file-bytes", "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()


def test_create_and_get_policy(client: TestClient) -> None:
    created = create_policy(client)

    assert created["status"] == "draft"
    assert created["version"] == 1
    assert "content" not in created

    response = client.get(f"/api/v1/policies/{created['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == "Data Retention Policy"


def test_get_missing_policy_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/policies/999")
    assert response.status_code == 404


def test_list_policies(client: TestClient) -> None:
    create_policy(client, title="Policy A")
    create_policy(client, title="Policy B")

    response = client.get("/api/v1/policies")

    assert response.status_code == 200
    titles = {p["title"] for p in response.json()}
    assert titles == {"Policy A", "Policy B"}


def test_update_policy_metadata_does_not_bump_version(client: TestClient) -> None:
    created = create_policy(client)
    policy_id = created["id"]

    response = client.put(f"/api/v1/policies/{policy_id}", json={"title": "Renamed Policy"})

    assert response.status_code == 200
    assert response.json()["title"] == "Renamed Policy"
    assert response.json()["version"] == 1


def test_update_policy_can_set_owner(client: TestClient, second_user: User) -> None:
    policy_id = create_policy(client)["id"]

    response = client.put(f"/api/v1/policies/{policy_id}", json={"owner_id": second_user.id})

    assert response.status_code == 200
    assert response.json()["owner_id"] == second_user.id


def test_uploading_a_document_bumps_version_and_appears_in_history(client: TestClient) -> None:
    policy_id = create_policy(client)["id"]

    upload_document(client, policy_id, filename="policy-draft.pdf")

    updated = client.get(f"/api/v1/policies/{policy_id}").json()
    assert updated["version"] == 2

    history = client.get(f"/api/v1/policies/{policy_id}/versions").json()
    assert len(history) == 1
    assert history[0]["action"] == "document_added"
    assert history[0]["diff"]["filename"] == "policy-draft.pdf"


def test_deleting_a_document_bumps_version_and_appears_in_history(client: TestClient) -> None:
    policy_id = create_policy(client)["id"]
    uploaded = upload_document(client, policy_id)

    client.delete(f"/api/v1/evidence/{uploaded['id']}")

    updated = client.get(f"/api/v1/policies/{policy_id}").json()
    assert updated["version"] == 3

    history = client.get(f"/api/v1/policies/{policy_id}/versions").json()
    actions = [entry["action"] for entry in history]
    assert actions == ["document_added", "document_removed"]


def test_uploading_a_document_does_not_bump_version_once_approved(
    client: TestClient,
    second_user: User,
    login_as: Callable[[User], None],
    make_caigo: Callable[[User], None],
) -> None:
    policy_id = create_policy(client)["id"]
    client.post(f"/api/v1/policies/{policy_id}/submit-for-review")
    make_caigo(second_user)
    login_as(second_user)
    approve_response = client.post(f"/api/v1/policies/{policy_id}/approve")
    assert approve_response.status_code == 200

    upload_document(client, policy_id)

    updated = client.get(f"/api/v1/policies/{policy_id}").json()
    assert updated["version"] == 1


def test_versions_endpoint_for_missing_policy_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/policies/999/versions")
    assert response.status_code == 404


def test_full_review_workflow(
    client: TestClient,
    second_user: User,
    login_as: Callable[[User], None],
    make_caigo: Callable[[User], None],
) -> None:
    policy_id = create_policy(client)["id"]

    submit_response = client.post(f"/api/v1/policies/{policy_id}/submit-for-review")
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "in_review"

    make_caigo(second_user)
    login_as(second_user)
    approve_response = client.post(f"/api/v1/policies/{policy_id}/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"


def test_cannot_approve_a_draft_policy(
    client: TestClient, second_user: User, login_as: Callable[[User], None]
) -> None:
    policy_id = create_policy(client)["id"]
    login_as(second_user)

    response = client.post(f"/api/v1/policies/{policy_id}/approve")

    assert response.status_code == 409


def test_cannot_approve_your_own_submission(
    client: TestClient, test_user: User, make_caigo: Callable[[User], None]
) -> None:
    make_caigo(test_user)
    policy_id = create_policy(client)["id"]
    client.post(f"/api/v1/policies/{policy_id}/submit-for-review")

    response = client.post(f"/api/v1/policies/{policy_id}/approve")

    assert response.status_code == 409
    assert "same user" in response.json()["detail"]


def test_non_caigo_admin_cannot_approve(
    client: TestClient, second_user: User, login_as: Callable[[User], None]
) -> None:
    policy_id = create_policy(client)["id"]
    client.post(f"/api/v1/policies/{policy_id}/submit-for-review")
    login_as(second_user)

    response = client.post(f"/api/v1/policies/{policy_id}/approve")

    assert response.status_code == 403


def test_an_active_caigo_delegate_can_approve(
    client: TestClient, db_session: Session, second_user: User, login_as: Callable[[User], None]
) -> None:
    """require_caigo (which every CAIGO-gated approval calls) goes through
    is_caigo, the same choke point a time-boxed delegate is recognized at --
    so a delegate with no real holder assignment can still approve here."""
    policy_id = create_policy(client)["id"]
    client.post(f"/api/v1/policies/{policy_id}/submit-for-review")
    governance_role_service.delegate_caigo(
        db_session, second_user.id, datetime.now(UTC) + timedelta(days=1), actor_id=None
    )
    login_as(second_user)

    response = client.post(f"/api/v1/policies/{policy_id}/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_cannot_edit_after_submitted_for_review(client: TestClient) -> None:
    policy_id = create_policy(client)["id"]
    client.post(f"/api/v1/policies/{policy_id}/submit-for-review")

    response = client.put(f"/api/v1/policies/{policy_id}", json={"title": "sneaky edit"})

    assert response.status_code == 409


def test_delete_draft_policy(client: TestClient) -> None:
    policy_id = create_policy(client)["id"]

    response = client.delete(f"/api/v1/policies/{policy_id}")
    assert response.status_code == 204

    assert client.get(f"/api/v1/policies/{policy_id}").status_code == 404


def test_cannot_delete_approved_policy(
    client: TestClient,
    second_user: User,
    login_as: Callable[[User], None],
    make_caigo: Callable[[User], None],
) -> None:
    policy_id = create_policy(client)["id"]
    client.post(f"/api/v1/policies/{policy_id}/submit-for-review")
    make_caigo(second_user)
    login_as(second_user)
    assert client.post(f"/api/v1/policies/{policy_id}/approve").status_code == 200

    response = client.delete(f"/api/v1/policies/{policy_id}")

    assert response.status_code == 409
