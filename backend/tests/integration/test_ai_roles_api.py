from fastapi.testclient import TestClient

from app.models.user import User


def make_system(client: TestClient, name: str = "Resume Screener") -> int:
    response = client.post("/api/v1/ai-system-inventory/rows", json={"data": {"name": name}})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def set_org_roles(client: TestClient, codes: list[str]):
    return client.put("/api/v1/organization-context", json={"ai_roles": codes})


def applicability(client: TestClient) -> dict:
    return client.get("/api/v1/eu-ai-act/applicability").json()


def lifecycle(client: TestClient, row_id: int) -> dict:
    return client.get(f"/api/v1/ai-systems/{row_id}/lifecycle").json()


def test_the_reference_list_is_grouped_by_main_role(client: TestClient, test_user: User) -> None:
    roles = client.get("/api/v1/ai-roles").json()

    by_code = {role["code"]: role for role in roles}
    assert by_code["developer"]["parent"] == "AI producer"
    assert by_code["ai_user"]["parent"] == "AI customer"
    assert by_code["ai_auditor"]["parent"] == "AI partner"
    assert all(role["label"] and role["description"] for role in roles)


def test_the_organizations_roles_are_saved_and_validated(
    client: TestClient, test_user: User
) -> None:
    saved = set_org_roles(client, ["ai_user", "developer"])

    assert saved.status_code == 200, saved.text
    assert saved.json()["ai_roles"] == ["developer", "ai_user"]
    assert client.get("/api/v1/organization-context").json()["ai_roles"] == ["developer", "ai_user"]
    assert set_org_roles(client, ["wizard"]).status_code == 400


def test_an_ai_system_follows_the_organization_until_it_sets_its_own(
    client: TestClient, test_user: User
) -> None:
    row_id = make_system(client)
    set_org_roles(client, ["developer"])

    inherited = lifecycle(client, row_id)
    assert (inherited["ai_roles"], inherited["effective_ai_roles"]) == (None, ["developer"])

    own = client.put(
        f"/api/v1/ai-systems/{row_id}/lifecycle/ai-roles", json={"ai_roles": ["ai_user"]}
    )
    assert own.status_code == 200, own.text
    assert (own.json()["ai_roles"], own.json()["effective_ai_roles"]) == (
        ["ai_user"],
        ["ai_user"],
    )

    # The organization changing no longer reaches it ...
    set_org_roles(client, ["developer", "designer"])
    assert lifecycle(client, row_id)["effective_ai_roles"] == ["ai_user"]

    # ... until the override is cleared.
    cleared = client.put(f"/api/v1/ai-systems/{row_id}/lifecycle/ai-roles", json={"ai_roles": None})
    assert cleared.json()["ai_roles"] is None
    assert cleared.json()["effective_ai_roles"] == ["developer", "designer"]


def test_an_empty_override_means_no_roles_for_that_system(
    client: TestClient, test_user: User
) -> None:
    row_id = make_system(client)
    set_org_roles(client, ["developer"])

    response = client.put(f"/api/v1/ai-systems/{row_id}/lifecycle/ai-roles", json={"ai_roles": []})

    assert response.json()["ai_roles"] == []
    assert response.json()["effective_ai_roles"] == []


def test_an_unknown_role_is_refused_for_an_ai_system(client: TestClient, test_user: User) -> None:
    row_id = make_system(client)

    response = client.put(
        f"/api/v1/ai-systems/{row_id}/lifecycle/ai-roles", json={"ai_roles": ["wizard"]}
    )

    assert response.status_code == 400


def test_the_eu_roles_are_suggested_until_the_organization_records_its_own(
    client: TestClient, test_user: User
) -> None:
    assert applicability(client)["suggested_roles"] == []

    set_org_roles(client, ["developer", "ai_user", "ai_auditor"])
    assert applicability(client)["suggested_roles"] == ["provider", "deployer"]

    client.put(
        "/api/v1/eu-ai-act/applicability",
        json={"in_scope": True, "is_deployer": True, "has_high_risk_systems": False},
    )
    assert applicability(client)["suggested_roles"] == []


def test_partner_roles_suggest_nothing(client: TestClient, test_user: User) -> None:
    set_org_roles(client, ["data_provider", "ai_evaluator"])

    assert applicability(client)["suggested_roles"] == []


def test_a_system_only_suggestion_never_comes_from_its_own_override(
    client: TestClient, test_user: User
) -> None:
    # The hint is about the organization, so one system's override doesn't
    # feed it.
    row_id = make_system(client)
    client.put(f"/api/v1/ai-systems/{row_id}/lifecycle/ai-roles", json={"ai_roles": ["developer"]})

    assert applicability(client)["suggested_roles"] == []
