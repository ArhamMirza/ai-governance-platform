from fastapi.testclient import TestClient

FACTORS = [
    "Accountability",
    "Explainability",
    "Transparency",
    "Fairness",
    "Environmental Impact",
    "Reliability",
    "Privacy",
    "Safety",
]


def create_ai_system_row(client: TestClient, **data) -> dict:
    payload = {"name": "Resume Screener", "risk_tier": "high"}
    payload.update(data)
    response = client.post("/api/v1/ai-system-inventory/rows", json={"data": payload})
    assert response.status_code == 201
    return response.json()


def create_risk_assessment(client: TestClient, ai_system_row_id: int | None = None) -> dict:
    if ai_system_row_id is None:
        ai_system_row_id = create_ai_system_row(client)["id"]
    response = client.post(
        "/api/v1/risk-assessments", json={"ai_system_row_id": ai_system_row_id}
    )
    assert response.status_code == 201
    return response.json()


def create_impact_assessment(client: TestClient, risk_assessment_id: int) -> dict:
    response = client.post(
        f"/api/v1/risk-assessments/{risk_assessment_id}/impact-assessments", json={}
    )
    assert response.status_code == 201
    return response.json()


def test_create_seeds_all_eight_impact_factors(client: TestClient) -> None:
    risk_assessment = create_risk_assessment(client)

    created = create_impact_assessment(client, risk_assessment["id"])

    assert created["status"] == "draft"
    assert sorted(f["factor"] for f in created["factors"]) == sorted(FACTORS)
    assert all(f["score"] is None for f in created["factors"])


def test_create_rejects_unknown_risk_assessment(client: TestClient) -> None:
    response = client.post("/api/v1/risk-assessments/999999/impact-assessments", json={})

    assert response.status_code == 404


def test_list_shows_assessments_shared_across_risk_assessments_for_the_same_system(
    client: TestClient,
) -> None:
    """An Impact Assessment is scoped to the AI system, not to one risk
    assessment run -- a second risk assessment for the same system should
    see the same impact assessment history."""
    ai_system = create_ai_system_row(client)
    first_ra = create_risk_assessment(client, ai_system["id"])
    second_ra = create_risk_assessment(client, ai_system["id"])
    create_impact_assessment(client, first_ra["id"])

    listing = client.get(
        f"/api/v1/risk-assessments/{second_ra['id']}/impact-assessments"
    ).json()

    assert len(listing) == 1


def test_update_narrative_fields(client: TestClient) -> None:
    risk_assessment = create_risk_assessment(client)
    created = create_impact_assessment(client, risk_assessment["id"])

    response = client.put(
        f"/api/v1/impact-assessments/{created['id']}",
        json={
            "status": "completed",
            "system_description": "Screens resumes for relevant experience.",
            "foreseeable_misuse": "Used as sole decision-maker without human review.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["system_description"] == "Screens resumes for relevant experience."
    assert body["foreseeable_misuse"] == "Used as sole decision-maker without human review."


def test_update_factor_with_benefits_harms_criteria_and_score(client: TestClient) -> None:
    risk_assessment = create_risk_assessment(client)
    created = create_impact_assessment(client, risk_assessment["id"])

    response = client.put(
        f"/api/v1/impact-assessments/{created['id']}/factors/Fairness",
        json={
            "benefits": "Standardizes screening criteria across applicants.",
            "harms": "May encode historical bias present in training data.",
            "criteria": "Score 4-5 if disparate impact testing shows no significant gap.",
            "score": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["factor"] == "Fairness"
    assert body["score"] == 3
    assert body["benefits"] == "Standardizes screening criteria across applicants."


def test_update_factor_rejects_score_out_of_range(client: TestClient) -> None:
    risk_assessment = create_risk_assessment(client)
    created = create_impact_assessment(client, risk_assessment["id"])

    response = client.put(
        f"/api/v1/impact-assessments/{created['id']}/factors/Safety",
        json={"score": 6},
    )

    assert response.status_code == 400


def test_update_factor_rejects_unknown_factor_name(client: TestClient) -> None:
    risk_assessment = create_risk_assessment(client)
    created = create_impact_assessment(client, risk_assessment["id"])

    response = client.put(
        f"/api/v1/impact-assessments/{created['id']}/factors/NotARealFactor",
        json={"score": 3},
    )

    assert response.status_code == 400


def test_delete_removes_the_assessment_and_its_factors(client: TestClient) -> None:
    risk_assessment = create_risk_assessment(client)
    created = create_impact_assessment(client, risk_assessment["id"])

    response = client.delete(f"/api/v1/impact-assessments/{created['id']}")
    assert response.status_code == 204

    get_response = client.get(f"/api/v1/impact-assessments/{created['id']}")
    assert get_response.status_code == 404


def test_impact_assessment_can_be_tagged_to_framework_controls(client: TestClient) -> None:
    risk_assessment = create_risk_assessment(client)
    created = create_impact_assessment(client, risk_assessment["id"])
    control_id = client.get(
        "/api/v1/framework-controls", params={"framework": "iso_42001"}
    ).json()[0]["id"]

    response = client.put(
        "/api/v1/framework-tags",
        params={"entity_type": "ImpactAssessment", "entity_id": created["id"]},
        json={"control_ids": [control_id]},
    )

    assert response.status_code == 200
    updated = client.get(f"/api/v1/impact-assessments/{created['id']}").json()
    assert [t["id"] for t in updated["framework_tags"]] == [control_id]
