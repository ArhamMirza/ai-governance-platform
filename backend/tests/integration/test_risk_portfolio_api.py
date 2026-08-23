from fastapi.testclient import TestClient

PAST_DEADLINE = "2020-01-01"


def make_system(client: TestClient, name: str) -> int:
    return client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": name}}
    ).json()["id"]


def make_assessment(client: TestClient, row_id: int) -> int:
    return client.post("/api/v1/risk-assessments", json={"ai_system_row_id": row_id}).json()[
        "id"
    ]


def add_item(client: TestClient, assessment_id: int, **data) -> None:
    client.post(f"/api/v1/risk-assessments/{assessment_id}/rows", json={"data": data})


def test_summary_is_empty_without_assessments(client: TestClient) -> None:
    response = client.get("/api/v1/risk-assessments/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_assessments"] == 0
    assert body["risk_items"]["total"] == 0
    assert body["assessments"] == []
    assert body["criteria"]["is_default"] is True


def test_summary_route_is_not_shadowed_by_the_id_route(client: TestClient) -> None:
    """/summary must resolve before /{risk_assessment_id}."""
    response = client.get("/api/v1/risk-assessments/summary")

    assert response.status_code == 200
    assert "total_assessments" in response.json()


def test_summary_rolls_up_items_per_assessment(client: TestClient) -> None:
    first = make_assessment(client, make_system(client, "Screener"))
    add_item(client, first, likelihood=5, impact=5, treatment_deadline=PAST_DEADLINE)
    add_item(client, first, likelihood=2, impact=2)

    second = make_assessment(client, make_system(client, "Chatbot"))
    add_item(client, second, likelihood=2, impact=3)

    body = client.get("/api/v1/risk-assessments/summary").json()

    assert body["total_assessments"] == 2
    assert body["high_risk_count"] == 1
    assert body["risk_items"]["total"] == 3
    assert body["risk_items"]["overdue_count"] == 1

    # Worst rating first.
    assert [a["id"] for a in body["assessments"]] == [first, second]
    worst = body["assessments"][0]
    assert worst["overall_risk_rating"] == 25
    assert worst["item_count"] == 2
    assert worst["high_count"] == 1
    assert worst["low_count"] == 1
    assert worst["overdue_count"] == 1


def test_summary_sorts_unrated_assessments_last(client: TestClient) -> None:
    rated = make_assessment(client, make_system(client, "Screener"))
    add_item(client, rated, likelihood=3, impact=3)
    unrated = make_assessment(client, make_system(client, "Chatbot"))

    body = client.get("/api/v1/risk-assessments/summary").json()

    assert [a["id"] for a in body["assessments"]] == [rated, unrated]
    assert body["assessments"][-1]["overall_risk_rating"] is None


def test_summary_matrix_counts_occupied_cells(client: TestClient) -> None:
    assessment = make_assessment(client, make_system(client, "Screener"))
    add_item(client, assessment, likelihood=4, impact=3)
    add_item(client, assessment, likelihood=4, impact=3)

    body = client.get("/api/v1/risk-assessments/summary").json()

    assert body["matrix"] == [{"likelihood": 4, "impact": 3, "count": 2}]


def test_summary_respects_configured_criteria(client: TestClient) -> None:
    assessment = make_assessment(client, make_system(client, "Screener"))
    add_item(client, assessment, likelihood=3, impact=3)  # score 9

    assert client.get("/api/v1/risk-assessments/summary").json()["high_risk_count"] == 0

    client.put("/api/v1/risk-criteria", json={"medium_min_score": 3, "high_min_score": 9})

    body = client.get("/api/v1/risk-assessments/summary").json()
    assert body["high_risk_count"] == 1
    assert body["assessments"][0]["high_count"] == 1
