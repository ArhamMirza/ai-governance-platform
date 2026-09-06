from fastapi.testclient import TestClient

from app.models.user import UserRole
from tests.helpers import complete_impact_assessment


def attention_item(body: dict, key: str) -> dict | None:
    return next((item for item in body["attention"] if item["key"] == key), None)


def test_summary_reflects_created_entities(client: TestClient) -> None:
    client.post("/api/v1/policies", json={"title": "Policy A"})
    policy_b = client.post("/api/v1/policies", json={"title": "Policy B"}).json()
    client.post(f"/api/v1/policies/{policy_b['id']}/submit-for-review")

    client.post("/api/v1/procedures", json={"title": "Procedure A"})

    row = client.post(
        "/api/v1/ai-system-inventory/rows",
        json={"data": {"name": "Resume Screener", "risk_tier": "high"}},
    ).json()

    complete_impact_assessment(client, row["id"])
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
    complete_impact_assessment(client, row["id"])
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
    complete_impact_assessment(client, row["id"])
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


def test_vacant_governance_roles_are_surfaced_and_clear_once_all_are_held(
    client: TestClient, make_user
) -> None:
    body = client.get("/api/v1/dashboard/summary").json()
    # All five default roles start vacant.
    assert attention_item(body, "vacant_governance_roles")["count"] == 5

    roles = client.get("/api/v1/governance-roles").json()
    for role in roles:
        user = make_user(role=UserRole.ADMIN)
        response = client.post(
            f"/api/v1/governance-roles/{role['id']}/assignments", json={"user_id": user.id}
        )
        assert response.status_code == 201, response.text

    body = client.get("/api/v1/dashboard/summary").json()
    assert attention_item(body, "vacant_governance_roles") is None


def test_ai_systems_without_an_owner_are_surfaced(client: TestClient) -> None:
    row = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Resume Screener"}}
    ).json()
    # Touch the lifecycle so it exists, but never set an owner.
    client.get(f"/api/v1/ai-systems/{row['id']}/lifecycle")

    body = client.get("/api/v1/dashboard/summary").json()
    assert attention_item(body, "ai_systems_without_owner")["count"] == 1

    client.put(f"/api/v1/ai-systems/{row['id']}/lifecycle/owner", json={"owner_id": 1})

    body = client.get("/api/v1/dashboard/summary").json()
    assert attention_item(body, "ai_systems_without_owner") is None


def test_risk_owner_not_a_real_account_is_surfaced_but_unset_is_not(
    client: TestClient, test_user
) -> None:
    row = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Resume Screener"}}
    ).json()
    complete_impact_assessment(client, row["id"])
    ra = client.post("/api/v1/risk-assessments", json={"ai_system_row_id": row["id"]}).json()

    client.post(
        f"/api/v1/risk-assessments/{ra['id']}/rows",
        json={"data": {"category": "Bias", "risk_owner": str(test_user.id)}},
    )
    client.post(
        f"/api/v1/risk-assessments/{ra['id']}/rows",
        json={"data": {"category": "Privacy"}},  # risk_owner left unset
    )
    client.post(
        f"/api/v1/risk-assessments/{ra['id']}/rows",
        json={"data": {"category": "Security", "risk_owner": "9999"}},
    )

    body = client.get("/api/v1/dashboard/summary").json()

    # Only the "9999" row (set, but not a real user) counts -- the valid
    # owner and the unset one don't.
    assert attention_item(body, "risk_owner_not_a_real_account")["count"] == 1


def test_data_owner_not_a_real_account_is_surfaced(client: TestClient, test_user) -> None:
    client.post(
        "/api/v1/data-inventory/rows",
        json={"data": {"dataset_name": "CVs", "data_owner": str(test_user.id)}},
    )
    client.post(
        "/api/v1/data-inventory/rows",
        json={"data": {"dataset_name": "Legacy export", "data_owner": "not-a-real-id"}},
    )

    body = client.get("/api/v1/dashboard/summary").json()

    assert attention_item(body, "data_owner_not_a_real_account")["count"] == 1
