from fastapi.testclient import TestClient


def get_control_id(client: TestClient, framework: str) -> int:
    return client.get("/api/v1/framework-controls", params={"framework": framework}).json()[0][
        "id"
    ]


def create_policy(client: TestClient) -> dict:
    return client.post("/api/v1/policies", json={"title": "Data Retention Policy"}).json()


def test_list_controls(client: TestClient) -> None:
    response = client.get("/api/v1/framework-controls")

    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert {"id", "framework", "code", "title", "description"} <= body[0].keys()


def test_list_controls_filtered_by_framework(client: TestClient) -> None:
    response = client.get("/api/v1/framework-controls", params={"framework": "eu_ai_act"})

    assert response.status_code == 200
    assert all(c["framework"] == "eu_ai_act" for c in response.json())


def test_get_tags_for_untagged_entity_is_empty(client: TestClient) -> None:
    response = client.get(
        "/api/v1/framework-tags", params={"entity_type": "Policy", "entity_id": 1}
    )

    assert response.status_code == 200
    assert response.json() == []


def test_set_and_read_back_tags_on_a_policy(client: TestClient) -> None:
    policy = create_policy(client)
    control_id = get_control_id(client, "iso_42001")

    put_response = client.put(
        "/api/v1/framework-tags",
        params={"entity_type": "Policy", "entity_id": policy["id"]},
        json={"control_ids": [control_id]},
    )
    assert put_response.status_code == 200
    assert [c["id"] for c in put_response.json()] == [control_id]

    get_response = client.get(
        "/api/v1/framework-tags", params={"entity_type": "Policy", "entity_id": policy["id"]}
    )
    assert [c["id"] for c in get_response.json()] == [control_id]


def test_set_tags_rejects_unknown_control_id(client: TestClient) -> None:
    policy = create_policy(client)

    response = client.put(
        "/api/v1/framework-tags",
        params={"entity_type": "Policy", "entity_id": policy["id"]},
        json={"control_ids": [999999]},
    )

    assert response.status_code == 400


def test_set_tags_is_visible_in_the_audit_log(client: TestClient) -> None:
    policy = create_policy(client)
    control_id = get_control_id(client, "iso_42001")

    client.put(
        "/api/v1/framework-tags",
        params={"entity_type": "Policy", "entity_id": policy["id"]},
        json={"control_ids": [control_id]},
    )

    response = client.get(
        "/api/v1/audit-log", params={"entity_type": "Policy", "entity_id": policy["id"]}
    )
    actions = [entry["action"] for entry in response.json()]
    assert "framework_tags_updated" in actions


def test_deleting_a_policy_clears_its_tags(client: TestClient) -> None:
    policy = create_policy(client)
    control_id = get_control_id(client, "iso_42001")
    client.put(
        "/api/v1/framework-tags",
        params={"entity_type": "Policy", "entity_id": policy["id"]},
        json={"control_ids": [control_id]},
    )

    delete_response = client.delete(f"/api/v1/policies/{policy['id']}")
    assert delete_response.status_code == 204

    tags = client.get(
        "/api/v1/framework-tags", params={"entity_type": "Policy", "entity_id": policy["id"]}
    ).json()
    assert tags == []
