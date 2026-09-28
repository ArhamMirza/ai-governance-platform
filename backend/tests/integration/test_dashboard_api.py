from fastapi.testclient import TestClient

from app.models.user import User, UserRole
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


def test_a_deactivated_owner_is_surfaced_the_same_as_no_owner(
    client: TestClient, make_user, login_as, test_user
) -> None:
    """A deactivated owner can't log in to approve and nobody may approve in
    their place, so the record is stuck -- it has to show up somewhere."""
    owner = make_user()
    row = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Resume Screener"}}
    ).json()
    client.put(
        f"/api/v1/ai-systems/{row['id']}/lifecycle/owner", json={"owner_id": owner.id}
    )
    body = client.get("/api/v1/dashboard/summary").json()
    assert attention_item(body, "ai_systems_without_owner") is None

    client.patch(f"/api/v1/users/{owner.id}", json={"is_active": False})

    body = client.get("/api/v1/dashboard/summary").json()
    assert attention_item(body, "ai_systems_without_owner")["count"] == 1


def test_a_deactivated_dataset_owner_is_surfaced(
    client: TestClient, make_user, test_user
) -> None:
    owner = make_user()
    client.post(
        "/api/v1/data-inventory/rows",
        json={"data": {"dataset_name": "Applicant CVs", "data_owner": str(owner.id)}},
    )
    body = client.get("/api/v1/dashboard/summary").json()
    assert attention_item(body, "data_owner_not_a_real_account") is None

    client.patch(f"/api/v1/users/{owner.id}", json={"is_active": False})

    body = client.get("/api/v1/dashboard/summary").json()
    assert attention_item(body, "data_owner_not_a_real_account")["count"] == 1


def test_accountabilities_are_readable_before_deactivating(
    client: TestClient, make_user
) -> None:
    owner = make_user()
    row = client.post(
        "/api/v1/ai-system-inventory/rows", json={"data": {"name": "Resume Screener"}}
    ).json()
    client.put(
        f"/api/v1/ai-systems/{row['id']}/lifecycle/owner", json={"owner_id": owner.id}
    )

    response = client.get(f"/api/v1/users/{owner.id}/accountabilities")

    assert response.status_code == 200
    assert response.json()["ai_systems_owned"] == ["Resume Screener"]


def test_accountabilities_require_manage_users(
    client: TestClient, make_user, login_as
) -> None:
    target = make_user()
    login_as(make_user(role=UserRole.CONTRIBUTOR))

    response = client.get(f"/api/v1/users/{target.id}/accountabilities")

    assert response.status_code == 403


# ---------- compliance rollup ----------


def any_clause_control(client: TestClient) -> dict:
    controls = client.get("/api/v1/framework-controls", params={"framework": "iso_42001"}).json()
    return next(c for c in controls if c["category"] == "clause")


def test_summary_compliance_matches_the_compliance_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard/summary")
    expected = client.get("/api/v1/compliance-status/summary").json()

    assert response.json()["compliance"] == expected


def test_an_uncovered_control_is_listed_as_needing_attention(client: TestClient) -> None:
    body = client.get("/api/v1/dashboard/summary").json()

    item = attention_item(body, "uncovered_framework_controls")

    assert item is not None
    # Nothing is tagged to anything on a fresh database, so every seeded
    # clause, Annex A control (all applicable by default) and EU AI Act
    # article counts as uncovered.
    assert item["count"] == 24 + 38 + 24


def test_tagging_a_control_to_an_approved_policy_removes_it_from_uncovered(
    client: TestClient,
    second_user: User,
    login_as,
    make_caigo,
) -> None:
    control = any_clause_control(client)
    policy = client.post("/api/v1/policies", json={"title": "Data Retention Policy"}).json()
    client.put(
        "/api/v1/framework-tags",
        params={"entity_type": "Policy", "entity_id": policy["id"]},
        json={"control_ids": [control["id"]]},
    )
    client.post(f"/api/v1/policies/{policy['id']}/submit-for-review")
    make_caigo(second_user)
    login_as(second_user)
    approve_response = client.post(f"/api/v1/policies/{policy['id']}/approve")
    assert approve_response.status_code == 200

    body = client.get("/api/v1/dashboard/summary").json()

    assert attention_item(body, "uncovered_framework_controls")["count"] == 24 + 38 + 24 - 1
    assert body["compliance"]["iso_42001_clauses"]["satisfied"] == 1


def test_tagging_a_control_to_a_draft_policy_counts_as_stale_not_uncovered(
    client: TestClient,
) -> None:
    control = any_clause_control(client)
    policy = client.post("/api/v1/policies", json={"title": "Data Retention Policy"}).json()
    client.put(
        "/api/v1/framework-tags",
        params={"entity_type": "Policy", "entity_id": policy["id"]},
        json={"control_ids": [control["id"]]},
    )

    body = client.get("/api/v1/dashboard/summary").json()

    assert attention_item(body, "uncovered_framework_controls")["count"] == 24 + 38 + 24 - 1
    assert attention_item(body, "stale_framework_controls")["count"] == 1
