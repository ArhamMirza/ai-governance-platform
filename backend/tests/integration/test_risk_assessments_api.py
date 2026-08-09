from fastapi.testclient import TestClient


def create_ai_system_row(client: TestClient, **data) -> dict:
    payload = {"name": "Resume Screener", "risk_tier": "high"}
    payload.update(data)
    response = client.post("/api/v1/ai-system-inventory/rows", json={"data": payload})
    assert response.status_code == 201
    return response.json()


def create_risk_assessment(client: TestClient, **overrides) -> dict:
    row = create_ai_system_row(client)
    payload = {"ai_system_row_id": row["id"]}
    payload.update(overrides)
    response = client.post("/api/v1/risk-assessments", json=payload)
    assert response.status_code == 201
    return response.json()


def test_create_risk_assessment_creates_sheet_with_default_columns(client: TestClient) -> None:
    created = create_risk_assessment(client)

    assert created["status"] == "draft"
    assert created["overall_risk_rating"] is None

    # Adding a row using every default-column key proves they all exist on
    # the sheet created for this assessment -- an unknown key would 400.
    response = client.post(
        f"/api/v1/risk-assessments/{created['id']}/rows",
        json={
            "data": {
                "category": "Bias",
                "description": "Model may exhibit demographic bias",
                "likelihood": 3,
                "impact": 4,
                "mitigation": "Add fairness testing",
                "residual_likelihood": 1,
                "residual_impact": 2,
                "control_owner": "ML Team",
                "status": "open",
            }
        },
    )
    assert response.status_code == 201


def test_set_columns_succeeds_when_reserved_columns_are_kept(client: TestClient) -> None:
    created = create_risk_assessment(client)

    response = client.put(
        f"/api/v1/risk-assessments/{created['id']}/columns",
        json={
            "columns": [
                {"key": "category", "label": "Category", "data_type": "text"},
                {"key": "likelihood", "label": "Likelihood", "data_type": "number"},
                {"key": "impact", "label": "Impact", "data_type": "number"},
                {
                    "key": "residual_likelihood",
                    "label": "Residual Likelihood",
                    "data_type": "number",
                },
                {"key": "residual_impact", "label": "Residual Impact", "data_type": "number"},
            ]
        },
    )

    assert response.status_code == 200


def test_set_columns_rejects_dropping_reserved_risk_columns(client: TestClient) -> None:
    created = create_risk_assessment(client)

    response = client.put(
        f"/api/v1/risk-assessments/{created['id']}/columns",
        json={
            "columns": [
                {"key": "category", "label": "Category", "data_type": "text"},
                {"key": "likelihood", "label": "Likelihood", "data_type": "number"},
                {"key": "impact", "label": "Impact", "data_type": "number"},
            ]
        },
    )

    assert response.status_code == 400


def test_create_risk_assessment_rejects_missing_ai_system_row(client: TestClient) -> None:
    response = client.post("/api/v1/risk-assessments", json={"ai_system_row_id": 999})

    assert response.status_code == 404


def test_get_missing_risk_assessment_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/risk-assessments/999")
    assert response.status_code == 404


def test_list_risk_assessments(client: TestClient) -> None:
    create_risk_assessment(client)
    create_risk_assessment(client)

    response = client.get("/api/v1/risk-assessments")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_risk_assessment_status_and_framework_tags(client: TestClient) -> None:
    created = create_risk_assessment(client)

    response = client.put(
        f"/api/v1/risk-assessments/{created['id']}",
        json={"status": "in_progress", "framework_tags": ["ISO42001:8.4"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["framework_tags"] == ["ISO42001:8.4"]


def test_add_row_and_compute_overall_risk_rating(client: TestClient) -> None:
    created = create_risk_assessment(client)
    ra_id = created["id"]

    client.post(
        f"/api/v1/risk-assessments/{ra_id}/rows",
        json={"data": {"category": "Bias", "likelihood": 3, "impact": 4}},
    )
    client.post(
        f"/api/v1/risk-assessments/{ra_id}/rows",
        json={"data": {"category": "Privacy", "likelihood": 5, "impact": 5}},
    )

    response = client.get(f"/api/v1/risk-assessments/{ra_id}")

    assert response.status_code == 200
    assert response.json()["overall_risk_rating"] == 25.0


def test_row_inherent_risk_score_is_computed(client: TestClient) -> None:
    created = create_risk_assessment(client)

    row = client.post(
        f"/api/v1/risk-assessments/{created['id']}/rows",
        json={"data": {"category": "Bias", "likelihood": 3, "impact": 4}},
    ).json()

    assert row["data"]["inherent_risk_score"] == 12.0


def test_update_row(client: TestClient) -> None:
    created = create_risk_assessment(client)
    row = client.post(
        f"/api/v1/risk-assessments/{created['id']}/rows",
        json={"data": {"category": "Bias"}},
    ).json()

    response = client.put(
        f"/api/v1/risk-assessments/{created['id']}/rows/{row['id']}",
        json={"data": {"likelihood": 2, "impact": 3}},
    )

    assert response.status_code == 200
    assert response.json()["data"]["inherent_risk_score"] == 6.0


def test_delete_row(client: TestClient) -> None:
    created = create_risk_assessment(client)
    row = client.post(
        f"/api/v1/risk-assessments/{created['id']}/rows",
        json={"data": {"category": "Bias"}},
    ).json()

    response = client.delete(f"/api/v1/risk-assessments/{created['id']}/rows/{row['id']}")

    assert response.status_code == 204


def test_delete_risk_assessment_also_removes_its_rows(client: TestClient) -> None:
    created = create_risk_assessment(client)
    client.post(
        f"/api/v1/risk-assessments/{created['id']}/rows", json={"data": {"category": "Bias"}}
    )

    response = client.delete(f"/api/v1/risk-assessments/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/v1/risk-assessments/{created['id']}").status_code == 404


def test_upload_replaces_columns_and_rows(client: TestClient) -> None:
    created = create_risk_assessment(client)

    response = client.post(
        f"/api/v1/risk-assessments/{created['id']}/upload",
        files={
            "file": (
                "risks.csv",
                b"Category,Likelihood,Impact\nBias,3,4\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["overall_risk_rating"] == 12.0


def test_export_returns_xlsx(client: TestClient) -> None:
    created = create_risk_assessment(client)
    client.post(
        f"/api/v1/risk-assessments/{created['id']}/rows", json={"data": {"category": "Bias"}}
    )

    response = client.get(f"/api/v1/risk-assessments/{created['id']}/export")

    assert response.status_code == 200
    assert response.content[:2] == b"PK"
