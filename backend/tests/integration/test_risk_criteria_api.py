from fastapi.testclient import TestClient

from app.models.risk_criteria import DEFAULT_HIGH_MIN_SCORE, DEFAULT_MEDIUM_MIN_SCORE


def test_get_returns_defaults_initially(client: TestClient) -> None:
    response = client.get("/api/v1/risk-criteria")

    assert response.status_code == 200
    body = response.json()
    assert body["medium_min_score"] == DEFAULT_MEDIUM_MIN_SCORE
    assert body["high_min_score"] == DEFAULT_HIGH_MIN_SCORE
    assert body["is_default"] is True
    assert body["min_score"] == 1
    assert body["max_score"] == 25


def test_put_updates_criteria(client: TestClient) -> None:
    response = client.put(
        "/api/v1/risk-criteria", json={"medium_min_score": 4, "high_min_score": 10}
    )

    assert response.status_code == 200
    assert response.json()["high_min_score"] == 10
    assert response.json()["is_default"] is False
    assert client.get("/api/v1/risk-criteria").json()["medium_min_score"] == 4


def test_put_rejects_overlapping_bands(client: TestClient) -> None:
    response = client.put(
        "/api/v1/risk-criteria", json={"medium_min_score": 12, "high_min_score": 8}
    )

    assert response.status_code == 400


def test_put_rejects_out_of_range_bands(client: TestClient) -> None:
    response = client.put(
        "/api/v1/risk-criteria", json={"medium_min_score": 5, "high_min_score": 99}
    )

    assert response.status_code == 400


def test_reset_restores_defaults(client: TestClient) -> None:
    client.put("/api/v1/risk-criteria", json={"medium_min_score": 3, "high_min_score": 7})

    response = client.post("/api/v1/risk-criteria/reset")

    assert response.status_code == 200
    assert response.json()["high_min_score"] == DEFAULT_HIGH_MIN_SCORE
    assert response.json()["is_default"] is True


def test_updates_are_audited(client: TestClient) -> None:
    client.put("/api/v1/risk-criteria", json={"medium_min_score": 4, "high_min_score": 10})

    response = client.get(
        "/api/v1/audit-log", params={"entity_type": "RiskCriteria", "entity_id": 1}
    )

    assert response.status_code == 200
    actions = [entry["action"] for entry in response.json()]
    assert "updated" in actions


def test_criteria_change_reshapes_dashboard_severity(client: TestClient) -> None:
    """A score of 9 moves from medium to high when the band is lowered."""
    row_id = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Screener"}}
    ).json()["id"]
    assessment = client.post(
        "/api/v1/risk-assessments", json={"ai_system_row_id": row_id}
    ).json()
    client.post(
        f"/api/v1/risk-assessments/{assessment['id']}/rows",
        json={"data": {"likelihood": 3, "impact": 3}},
    )

    before = client.get("/api/v1/dashboard/summary").json()
    assert before["risk_items"]["by_severity"]["medium"] == 1
    assert before["risk_items"]["by_severity"]["high"] == 0

    client.put("/api/v1/risk-criteria", json={"medium_min_score": 3, "high_min_score": 9})

    after = client.get("/api/v1/dashboard/summary").json()
    assert after["risk_items"]["by_severity"]["high"] == 1
    assert after["risk_assessments"]["high_risk_count"] == 1
    assert after["criteria"]["high_min_score"] == 9
