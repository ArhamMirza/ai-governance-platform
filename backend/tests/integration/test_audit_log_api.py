from fastapi.testclient import TestClient


def test_lists_entries_for_the_requested_entity(client: TestClient) -> None:
    policy = client.post("/api/v1/policies", json={"title": "Data Retention Policy"}).json()

    response = client.get(
        "/api/v1/audit-log", params={"entity_type": "Policy", "entity_id": policy["id"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["action"] == "created"
    assert body[0]["entity_type"] == "Policy"
    assert body[0]["entity_id"] == policy["id"]


def test_accumulates_multiple_actions_in_order(client: TestClient) -> None:
    policy = client.post("/api/v1/policies", json={"title": "Data Retention Policy"}).json()
    client.post(f"/api/v1/policies/{policy['id']}/submit-for-review")
    client.post(f"/api/v1/policies/{policy['id']}/approve")

    response = client.get(
        "/api/v1/audit-log", params={"entity_type": "Policy", "entity_id": policy["id"]}
    )

    actions = [entry["action"] for entry in response.json()]
    assert actions == ["created", "submitted_for_review", "approved"]


def test_does_not_mix_entries_across_different_entities(client: TestClient) -> None:
    policy_a = client.post("/api/v1/policies", json={"title": "Policy A"}).json()
    client.post("/api/v1/policies", json={"title": "Policy B"}).json()

    response = client.get(
        "/api/v1/audit-log", params={"entity_type": "Policy", "entity_id": policy_a["id"]}
    )

    assert len(response.json()) == 1


def test_returns_empty_list_for_an_entity_with_no_history(client: TestClient) -> None:
    response = client.get(
        "/api/v1/audit-log", params={"entity_type": "Policy", "entity_id": 999}
    )

    assert response.status_code == 200
    assert response.json() == []
