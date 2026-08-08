from fastapi.testclient import TestClient


def create_policy(client: TestClient, **overrides) -> dict:
    payload = {"title": "Data Retention Policy", "content": "Initial text"}
    payload.update(overrides)
    response = client.post("/api/v1/policies", json=payload)
    assert response.status_code == 201
    return response.json()


def test_create_and_get_policy(client: TestClient) -> None:
    created = create_policy(client)

    assert created["status"] == "draft"
    assert created["version"] == 1

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


def test_update_policy_creates_new_version(client: TestClient) -> None:
    created = create_policy(client)
    policy_id = created["id"]

    response = client.put(
        f"/api/v1/policies/{policy_id}",
        json={"content": "Revised text", "change_note": "clarified scope"},
    )

    assert response.status_code == 200
    assert response.json()["version"] == 2

    versions = client.get(f"/api/v1/policies/{policy_id}/versions").json()
    assert len(versions) == 2
    assert versions[1]["change_note"] == "clarified scope"


def test_full_review_workflow(client: TestClient) -> None:
    policy_id = create_policy(client)["id"]

    submit_response = client.post(f"/api/v1/policies/{policy_id}/submit-for-review")
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "in_review"

    approve_response = client.post(f"/api/v1/policies/{policy_id}/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"


def test_cannot_approve_a_draft_policy(client: TestClient) -> None:
    policy_id = create_policy(client)["id"]

    response = client.post(f"/api/v1/policies/{policy_id}/approve")

    assert response.status_code == 409


def test_cannot_edit_after_submitted_for_review(client: TestClient) -> None:
    policy_id = create_policy(client)["id"]
    client.post(f"/api/v1/policies/{policy_id}/submit-for-review")

    response = client.put(f"/api/v1/policies/{policy_id}", json={"content": "sneaky edit"})

    assert response.status_code == 409


def test_delete_draft_policy(client: TestClient) -> None:
    policy_id = create_policy(client)["id"]

    response = client.delete(f"/api/v1/policies/{policy_id}")
    assert response.status_code == 204

    assert client.get(f"/api/v1/policies/{policy_id}").status_code == 404


def test_cannot_delete_approved_policy(client: TestClient) -> None:
    policy_id = create_policy(client)["id"]
    client.post(f"/api/v1/policies/{policy_id}/submit-for-review")
    client.post(f"/api/v1/policies/{policy_id}/approve")

    response = client.delete(f"/api/v1/policies/{policy_id}")

    assert response.status_code == 409
