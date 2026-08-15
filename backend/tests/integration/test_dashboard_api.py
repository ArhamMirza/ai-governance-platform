from fastapi.testclient import TestClient


def test_summary_reflects_created_entities(client: TestClient) -> None:
    client.post("/api/v1/policies", json={"title": "Policy A"})
    policy_b = client.post("/api/v1/policies", json={"title": "Policy B"}).json()
    client.post(f"/api/v1/policies/{policy_b['id']}/submit-for-review")

    client.post("/api/v1/procedures", json={"title": "Procedure A"})

    row = client.post(
        "/api/v1/ai-system-inventory/rows",
        json={"data": {"name": "Resume Screener", "risk_tier": "high"}},
    ).json()

    risk_assessment = client.post(
        "/api/v1/risk-assessments", json={"ai_system_row_id": row["id"]}
    ).json()
    client.post(
        f"/api/v1/risk-assessments/{risk_assessment['id']}/rows",
        json={"data": {"category": "Bias", "likelihood": 5, "impact": 5}},
    )

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["policies"] == {"total": 2, "by_status": {"draft": 1, "in_review": 1}}
    assert body["procedures"] == {"total": 1, "by_status": {"draft": 1}}
    assert body["ai_systems"] == {"total": 1, "by_risk_tier": {"high": 1}}
    assert body["risk_assessments"]["total"] == 1
    assert body["risk_assessments"]["by_status"] == {"draft": 1}
    assert body["risk_assessments"]["high_risk_count"] == 1


def test_summary_on_empty_database(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["policies"] == {"total": 0, "by_status": {}}
    assert body["procedures"] == {"total": 0, "by_status": {}}
    assert body["ai_systems"] == {"total": 0, "by_risk_tier": {}}
    assert body["risk_assessments"] == {"total": 0, "by_status": {}, "high_risk_count": 0}
