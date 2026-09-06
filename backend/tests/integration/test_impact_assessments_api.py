from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services import impact_assessment_service
from tests.helpers import complete_impact_assessment


def approve_impact_assessment(db_session: Session, impact_assessment_id: int) -> None:
    """Walks an assessment through owner and CAIGO approval with no real
    actor, same no-op-on-None behavior audit_service.require_different_approver
    already has -- for tests that only care about what completing does, not
    who is allowed to do it."""
    impact_assessment_service.submit_for_owner_approval(
        db_session, impact_assessment_id, actor_id=None
    )
    impact_assessment_service.approve_owner_stage(
        db_session, impact_assessment_id, actor_id=None
    )
    impact_assessment_service.approve_caigo_stage(
        db_session, impact_assessment_id, actor_id=None
    )

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


def create_impact_assessment(client: TestClient, ai_system_row_id: int | None = None) -> dict:
    """The primary path -- straight against an AI system, no risk assessment
    needed (and none can exist yet, since impact assessment comes first)."""
    if ai_system_row_id is None:
        ai_system_row_id = create_ai_system_row(client)["id"]
    response = client.post(
        "/api/v1/impact-assessments", json={"ai_system_row_id": ai_system_row_id}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_seeds_all_eight_impact_factors(client: TestClient) -> None:
    created = create_impact_assessment(client)

    assert created["status"] == "draft"
    assert sorted(f["factor"] for f in created["factors"]) == sorted(FACTORS)
    assert all(f["score"] is None for f in created["factors"])


def test_create_rejects_unknown_ai_system(client: TestClient) -> None:
    response = client.post("/api/v1/impact-assessments", json={"ai_system_row_id": 999999})

    assert response.status_code == 404


def test_list_filters_by_ai_system(client: TestClient) -> None:
    first = create_ai_system_row(client, name="First")
    second = create_ai_system_row(client, name="Second")
    create_impact_assessment(client, first["id"])
    create_impact_assessment(client, second["id"])

    listing = client.get(
        "/api/v1/impact-assessments", params={"ai_system_row_id": first["id"]}
    ).json()

    assert [a["ai_system_row_id"] for a in listing] == [first["id"]]


def test_only_one_impact_assessment_per_ai_system(client: TestClient) -> None:
    ai_system = create_ai_system_row(client)
    create_impact_assessment(client, ai_system["id"])

    response = client.post(
        "/api/v1/impact-assessments", json={"ai_system_row_id": ai_system["id"]}
    )

    assert response.status_code == 409
    assert "already has an impact assessment" in response.text


def test_risk_assessment_sees_its_systems_impact_assessment(client: TestClient) -> None:
    ai_system = create_ai_system_row(client)
    complete_impact_assessment(client, ai_system["id"])
    risk_assessment = client.post(
        "/api/v1/risk-assessments", json={"ai_system_row_id": ai_system["id"]}
    ).json()

    listing = client.get(
        f"/api/v1/risk-assessments/{risk_assessment['id']}/impact-assessments"
    ).json()

    assert len(listing) == 1
    assert listing[0]["ai_system_row_id"] == ai_system["id"]


def test_completing_sets_the_yearly_review_date(
    client: TestClient, db_session: Session
) -> None:
    created = create_impact_assessment(client)

    approve_impact_assessment(db_session, created["id"])

    body = client.get(f"/api/v1/impact-assessments/{created['id']}").json()
    assert body["status"] == "completed"
    assert body["assessment_date"] is not None
    assert body["next_review_date"][:4] == str(int(body["assessment_date"][:4]) + 1)
    assert body["review_overdue"] is False


def test_update_narrative_fields(client: TestClient, db_session: Session) -> None:
    created = create_impact_assessment(client)

    response = client.put(
        f"/api/v1/impact-assessments/{created['id']}",
        json={
            "system_description": "Screens resumes for relevant experience.",
            "foreseeable_misuse": "Used as sole decision-maker without human review.",
        },
    )
    assert response.status_code == 200
    approve_impact_assessment(db_session, created["id"])

    body = client.get(f"/api/v1/impact-assessments/{created['id']}").json()
    assert body["status"] == "completed"
    assert body["system_description"] == "Screens resumes for relevant experience."
    assert body["foreseeable_misuse"] == "Used as sole decision-maker without human review."


def test_update_factor_with_benefits_harms_criteria_and_score(client: TestClient) -> None:
    created = create_impact_assessment(client)

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
    created = create_impact_assessment(client)

    response = client.put(
        f"/api/v1/impact-assessments/{created['id']}/factors/Safety",
        json={"score": 6},
    )

    assert response.status_code == 400


def test_update_factor_rejects_unknown_factor_name(client: TestClient) -> None:
    created = create_impact_assessment(client)

    response = client.put(
        f"/api/v1/impact-assessments/{created['id']}/factors/NotARealFactor",
        json={"score": 3},
    )

    assert response.status_code == 400


def test_delete_removes_the_assessment_and_its_factors(client: TestClient) -> None:
    created = create_impact_assessment(client)

    response = client.delete(f"/api/v1/impact-assessments/{created['id']}")
    assert response.status_code == 204

    get_response = client.get(f"/api/v1/impact-assessments/{created['id']}")
    assert get_response.status_code == 404


def test_impact_assessment_can_be_tagged_to_framework_controls(client: TestClient) -> None:
    created = create_impact_assessment(client)
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
