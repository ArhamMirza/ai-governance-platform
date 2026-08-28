from fastapi.testclient import TestClient


def create_ai_system_row(client: TestClient, **data) -> dict:
    payload = {"name": "Resume Screener", "risk_tier": "high"}
    payload.update(data)
    response = client.post("/api/v1/ai-system-inventory/rows", json={"data": payload})
    assert response.status_code == 201
    return response.json()


def test_get_creates_singleton_with_default_columns(client: TestClient) -> None:
    response = client.get("/api/v1/data-inventory")

    assert response.status_code == 200
    body = response.json()
    assert body["entity_type"] == "DataInventory"
    assert [c["key"] for c in body["columns"]] == [
        "dataset_name",
        "ai_system_row_id",
        "data_type",
        "data_source",
        "personal_data_involved",
        "data_owner",
        "classification",
        "retention_period",
        "data_acquisition",
        "data_quality_measures",
        "data_provenance",
        "data_preparation",
    ]
    assert body["rows"] == []


def test_add_row_linked_to_an_ai_system(client: TestClient) -> None:
    ai_system = create_ai_system_row(client)

    response = client.post(
        "/api/v1/data-inventory/rows",
        json={
            "data": {
                "dataset_name": "Resume corpus",
                "ai_system_row_id": str(ai_system["id"]),
                "data_type": "training",
            }
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["ai_system_row_id"] == str(ai_system["id"])

    listing = client.get("/api/v1/data-inventory").json()
    assert len(listing["rows"]) == 1


def test_add_row_rejects_unknown_column(client: TestClient) -> None:
    response = client.post("/api/v1/data-inventory/rows", json={"data": {"not_a_column": "x"}})

    assert response.status_code == 400


def test_delete_row(client: TestClient) -> None:
    row = client.post(
        "/api/v1/data-inventory/rows", json={"data": {"dataset_name": "Resume corpus"}}
    ).json()

    response = client.delete(f"/api/v1/data-inventory/rows/{row['id']}")

    assert response.status_code == 204
    listing = client.get("/api/v1/data-inventory").json()
    assert listing["rows"] == []


def test_row_changes_are_audit_logged(client: TestClient) -> None:
    sheet_id = client.get("/api/v1/data-inventory").json()["id"]
    row = client.post(
        "/api/v1/data-inventory/rows", json={"data": {"dataset_name": "Resume corpus"}}
    ).json()
    client.put(
        f"/api/v1/data-inventory/rows/{row['id']}", json={"data": {"data_type": "training"}}
    )
    client.delete(f"/api/v1/data-inventory/rows/{row['id']}")

    history = client.get(
        "/api/v1/audit-log", params={"entity_type": "DataInventory", "entity_id": sheet_id}
    ).json()

    assert [entry["action"] for entry in history] == ["row_added", "row_updated", "row_deleted"]
