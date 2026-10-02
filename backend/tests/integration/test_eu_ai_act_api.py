from fastapi.testclient import TestClient

from app.models.user import User


def article(client: TestClient, code: str) -> dict:
    return next(a for a in client.get("/api/v1/eu-ai-act/articles").json() if a["code"] == code)


def compliance_summary(client: TestClient) -> dict:
    return client.get("/api/v1/compliance-status/summary").json()


def uncovered_count(client: TestClient) -> int:
    attention = client.get("/api/v1/dashboard/summary").json()["attention"]
    item = next((a for a in attention if a["key"] == "uncovered_framework_controls"), None)
    return item["count"] if item else 0


def test_starts_not_assessed_with_every_article_applicable(
    client: TestClient, test_user: User
) -> None:
    body = client.get("/api/v1/eu-ai-act/applicability").json()

    assert body["scope"] == "not_assessed"
    assert compliance_summary(client)["eu_ai_act"]["not_applicable"] == 0
    attention = client.get("/api/v1/dashboard/summary").json()["attention"]
    assert any(a["key"] == "eu_ai_act_not_assessed" for a in attention)


def test_out_of_scope_needs_a_justification(client: TestClient, test_user: User) -> None:
    response = client.put("/api/v1/eu-ai-act/applicability", json={"in_scope": False})

    assert response.status_code == 400


def test_in_scope_needs_a_role_and_the_high_risk_answer(
    client: TestClient, test_user: User
) -> None:
    no_role = client.put(
        "/api/v1/eu-ai-act/applicability", json={"in_scope": True, "has_high_risk_systems": True}
    )
    no_answer = client.put(
        "/api/v1/eu-ai-act/applicability", json={"in_scope": True, "is_deployer": True}
    )

    assert (no_role.status_code, no_answer.status_code) == (400, 400)


def test_out_of_scope_excludes_every_article_and_clears_the_alerts(
    client: TestClient, test_user: User
) -> None:
    uncovered_before = uncovered_count(client)

    response = client.put(
        "/api/v1/eu-ai-act/applicability",
        json={"in_scope": False, "scope_justification": "No EU market, users or outputs."},
    )

    assert response.status_code == 200
    assert response.json()["scope"] == "out_of_scope"
    summary = compliance_summary(client)
    assert summary["eu_ai_act_scope"] == "out_of_scope"
    eu = summary["eu_ai_act"]
    assert eu["satisfied"] + eu["partial"] + eu["no_coverage"] == 0
    assert eu["not_applicable"] == 24
    assert uncovered_count(client) == uncovered_before - 24
    attention = client.get("/api/v1/dashboard/summary").json()["attention"]
    assert not any(a["key"] == "eu_ai_act_not_assessed" for a in attention)


def test_a_deployer_sees_only_deployer_and_general_articles(
    client: TestClient, test_user: User
) -> None:
    client.put(
        "/api/v1/eu-ai-act/applicability",
        json={"in_scope": True, "is_deployer": True, "has_high_risk_systems": True},
    )

    applicable = {
        a["code"] for a in client.get("/api/v1/eu-ai-act/articles").json() if a["applicable"]
    }
    assert applicable == {"Art.6", "Art.7", "Art.25", "Art.26", "Art.27"}
    assert "providers" in article(client, "Art.16")["reason"]


def test_an_override_wins_in_either_direction_and_can_be_cleared(
    client: TestClient, test_user: User
) -> None:
    client.put(
        "/api/v1/eu-ai-act/applicability",
        json={"in_scope": True, "is_deployer": True, "has_high_risk_systems": True},
    )
    art16, art26 = article(client, "Art.16"), article(client, "Art.26")

    client.put(
        f"/api/v1/eu-ai-act/articles/{art16['id']}/override",
        json={"applicability": "applicable", "justification": "We took on provider duties."},
    )
    client.put(
        f"/api/v1/eu-ai-act/articles/{art26['id']}/override",
        json={"applicability": "not_applicable", "justification": "Covered by the group entity."},
    )

    assert article(client, "Art.16")["applicable"] is True
    assert article(client, "Art.16")["automatic_applicable"] is False
    assert article(client, "Art.26")["applicable"] is False
    statuses = {
        s["code"]: s["status"]
        for s in client.get("/api/v1/compliance-status", params={"framework": "eu_ai_act"}).json()
    }
    assert statuses["Art.16"] != "not_applicable"
    assert statuses["Art.26"] == "not_applicable"

    client.delete(f"/api/v1/eu-ai-act/articles/{art16['id']}/override")
    assert article(client, "Art.16")["applicable"] is False
    assert article(client, "Art.16")["override_applicability"] is None


def test_an_override_needs_a_justification(client: TestClient, test_user: User) -> None:
    art6 = article(client, "Art.6")

    response = client.put(
        f"/api/v1/eu-ai-act/articles/{art6['id']}/override",
        json={"applicability": "not_applicable", "justification": "  "},
    )

    assert response.status_code == 400


def test_annex_a_statement_of_applicability_is_unaffected(
    client: TestClient, test_user: User
) -> None:
    client.put(
        "/api/v1/eu-ai-act/applicability",
        json={"in_scope": False, "scope_justification": "No EU nexus."},
    )

    annex_a = compliance_summary(client)["iso_42001_annex_a"]
    assert annex_a["not_applicable"] == 0
    assert len(client.get("/api/v1/framework-soa").json()) == 38
