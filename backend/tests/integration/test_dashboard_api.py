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
    assert body["my_risk_items"] == []


def test_my_risk_items_lists_open_items_owned_by_the_current_user(
    client: TestClient, test_user
) -> None:
    row = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Resume Screener"}}
    ).json()
    ra = client.post("/api/v1/risk-assessments", json={"ai_system_row_id": row["id"]}).json()

    mine = client.post(
        f"/api/v1/risk-assessments/{ra['id']}/rows",
        json={
            "data": {
                "category": "Bias",
                "likelihood": 3,
                "impact": 3,
                "risk_owner": str(test_user.id),
                "status": "open",
            }
        },
    ).json()
    client.post(
        f"/api/v1/risk-assessments/{ra['id']}/rows",
        json={"data": {"category": "Privacy", "risk_owner": "9999", "status": "open"}},
    )

    response = client.get("/api/v1/dashboard/summary")

    body = response.json()
    assert [item["row_id"] for item in body["my_risk_items"]] == [mine["id"]]
    assert body["my_risk_items"][0]["risk_assessment_id"] == ra["id"]
    assert body["my_risk_items"][0]["category"] == "Bias"


def test_my_risk_items_excludes_closed_items(client: TestClient, test_user) -> None:
    row = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Resume Screener"}}
    ).json()
    ra = client.post("/api/v1/risk-assessments", json={"ai_system_row_id": row["id"]}).json()
    item = client.post(
        f"/api/v1/risk-assessments/{ra['id']}/rows",
        json={"data": {"category": "Bias", "risk_owner": str(test_user.id)}},
    ).json()
    client.post(
        "/api/v1/evidence",
        data={"entity_type": "RiskItem", "entity_id": str(item["id"])},
        files={"file": ("proof.pdf", b"bytes", "application/pdf")},
    )
    client.post(f"/api/v1/risk-assessments/{ra['id']}/rows/{item['id']}/close")

    response = client.get("/api/v1/dashboard/summary")

    assert response.json()["my_risk_items"] == []
