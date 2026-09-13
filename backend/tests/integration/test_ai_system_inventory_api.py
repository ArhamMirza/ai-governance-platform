from fastapi.testclient import TestClient

from tests.helpers import complete_impact_assessment


def test_get_creates_singleton_with_default_columns(client: TestClient) -> None:
    response = client.get("/api/v1/ai-system-inventory")

    assert response.status_code == 200
    body = response.json()
    assert body["entity_type"] == "AISystemInventory"
    assert [c["key"] for c in body["columns"]] == [
        "name",
        "description",
        "purpose",
        "lifecycle_stage",
        "risk_tier",
        "resource_documentation",
        "data_resources",
        "tooling_frameworks",
        "tooling_documentation",
        "compute_infrastructure",
        "hosting_environment",
        "development_team",
        "oversight_roles",
    ]
    assert body["rows"] == []


def test_get_is_idempotent_returns_same_sheet(client: TestClient) -> None:
    first = client.get("/api/v1/ai-system-inventory").json()
    second = client.get("/api/v1/ai-system-inventory").json()

    assert first["id"] == second["id"]


def test_add_row(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ai-system-inventory/rows",
        json={"data": {"name": "Resume Screener", "risk_tier": "high"}},
    )

    assert response.status_code == 201
    body = response.json()
    # Every new system starts at Inception -- the stage is server-owned.
    assert body["data"] == {
        "name": "Resume Screener",
        "risk_tier": "high",
        "lifecycle_stage": "inception",
    }

    listing = client.get("/api/v1/ai-system-inventory").json()
    assert len(listing["rows"]) == 1


def test_add_row_rejects_unknown_column(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"not_a_column": "x"}}
    )

    assert response.status_code == 400


def test_update_row(client: TestClient) -> None:
    row = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Resume Screener"}}
    ).json()

    response = client.put(
        f"/api/v1/ai-system-inventory/rows/{row['id']}",
        json={"data": {"risk_tier": "high"}},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "name": "Resume Screener",
        "risk_tier": "high",
        "lifecycle_stage": "inception",
    }


def test_delete_row(client: TestClient) -> None:
    row = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Resume Screener"}}
    ).json()

    response = client.delete(f"/api/v1/ai-system-inventory/rows/{row['id']}")

    assert response.status_code == 204
    listing = client.get("/api/v1/ai-system-inventory").json()
    assert listing["rows"] == []


def test_set_columns_replaces_defaults(client: TestClient) -> None:
    response = client.put(
        "/api/v1/ai-system-inventory/columns",
        json={
            "columns": [
                {"key": "name", "label": "Name", "data_type": "text"},
                {"key": "lifecycle_stage", "label": "Lifecycle Stage", "data_type": "text"},
            ]
        },
    )

    assert response.status_code == 200
    assert [c["key"] for c in response.json()["columns"]] == ["name", "lifecycle_stage"]


def test_set_columns_rejects_dropping_the_lifecycle_stage_column(client: TestClient) -> None:
    """The stage drives the gates, so the column can't be removed."""
    response = client.put(
        "/api/v1/ai-system-inventory/columns",
        json={"columns": [{"key": "name", "label": "Name", "data_type": "text"}]},
    )

    assert response.status_code == 400
    assert "lifecycle_stage" in response.text


def test_upload_replaces_columns_and_rows(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ai-system-inventory/upload",
        files={
            "file": (
                "inventory.csv",
                b"Name,Risk Tier\nResume Screener,high\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    # lifecycle_stage is server-owned, so it survives an upload that doesn't
    # mention it -- the stage behind it still exists either way.
    assert [c["key"] for c in body["columns"]] == ["name", "risk_tier", "lifecycle_stage"]
    assert body["rows"][0]["data"] == {"name": "Resume Screener", "risk_tier": "high"}


def test_export_returns_xlsx(client: TestClient) -> None:
    client.post("/api/v1/ai-system-inventory/rows", json={"data": {"name": "Resume Screener"}})

    response = client.get("/api/v1/ai-system-inventory/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.content[:2] == b"PK"  # xlsx files are zip archives


def test_row_and_column_changes_are_audit_logged(client: TestClient) -> None:
    sheet_id = client.get("/api/v1/ai-system-inventory").json()["id"]
    row = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Resume Screener"}}
    ).json()
    client.put(
        f"/api/v1/ai-system-inventory/rows/{row['id']}", json={"data": {"risk_tier": "high"}}
    )
    client.delete(f"/api/v1/ai-system-inventory/rows/{row['id']}")

    history = client.get(
        "/api/v1/audit-log", params={"entity_type": "AISystemInventory", "entity_id": sheet_id}
    ).json()

    assert [entry["action"] for entry in history] == ["row_added", "row_updated", "row_deleted"]


def test_deleting_an_ai_system_deletes_its_assessments(client: TestClient) -> None:
    """The assessments describe a system that no longer exists, so they go
    with it rather than being left orphaned."""
    row = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Resume Screener"}}
    ).json()
    impact = complete_impact_assessment(client, row["id"])
    risk = client.post(
        "/api/v1/risk-assessments", json={"ai_system_row_id": row["id"]}
    ).json()

    response = client.delete(f"/api/v1/ai-system-inventory/rows/{row['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/v1/impact-assessments/{impact['id']}").status_code == 404
    assert client.get(f"/api/v1/risk-assessments/{risk['id']}").status_code == 404


def test_deleting_an_ai_system_without_assessments_still_works(client: TestClient) -> None:
    row = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Unassessed"}}
    ).json()

    assert client.delete(f"/api/v1/ai-system-inventory/rows/{row['id']}").status_code == 204


def test_reimport_matches_the_exported_id_and_leaves_an_unmatched_row_alone(
    client: TestClient,
) -> None:
    """A re-upload used to delete and recreate every row, and SQLite reuses
    a freed id -- silently attaching an unrelated existing system's life
    cycle to whatever new row landed on it. The exported ID column is how a
    re-upload recognizes its own rows now; one the file doesn't mention is
    left as it was, not dropped."""
    kept = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Fraud Detector"}}
    ).json()
    edited = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Resume Screener"}}
    ).json()

    # A file that mentions only the row being edited, by the id export_xlsx
    # would have given it -- the same round trip a real re-upload follows.
    csv_content = f"ID,Name\n{edited['id']},Resume Screener v2\n".encode()

    response = client.post(
        "/api/v1/ai-system-inventory/upload",
        files={"file": ("reimport.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    listing = client.get("/api/v1/ai-system-inventory").json()
    rows_by_id = {row["id"]: row["data"] for row in listing["rows"]}
    assert len(rows_by_id) == 2
    assert rows_by_id[kept["id"]]["name"] == "Fraud Detector"
    assert rows_by_id[edited["id"]]["name"] == "Resume Screener v2"
