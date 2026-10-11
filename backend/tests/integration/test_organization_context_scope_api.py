from fastapi.testclient import TestClient

from app.models.user import User


def clause_id(client: TestClient, code: str) -> int:
    controls = client.get("/api/v1/framework-controls", params={"framework": "iso_42001"}).json()
    return next(c["id"] for c in controls if c["code"] == code)


def test_the_scope_is_saved_and_read_back(client: TestClient, test_user: User) -> None:
    assert client.get("/api/v1/organization-context").json()["aims_scope"] is None

    response = client.put(
        "/api/v1/organization-context",
        json={"aims_scope": "Every production AI system.", "aims_scope_exclusions": "Prototypes."},
    )

    assert response.status_code == 200, response.text
    body = client.get("/api/v1/organization-context").json()
    assert body["aims_scope"] == "Every production AI system."
    assert body["aims_scope_exclusions"] == "Prototypes."


def test_the_context_can_be_tagged_and_shows_in_compliance_status(
    client: TestClient, test_user: User
) -> None:
    context = client.get("/api/v1/organization-context").json()
    scope_clause = clause_id(client, "4.3")

    tagged = client.put(
        "/api/v1/framework-tags",
        params={"entity_type": "OrganizationContext", "entity_id": context["id"]},
        json={"control_ids": [scope_clause]},
    )

    assert tagged.status_code == 200, tagged.text
    rows = client.get("/api/v1/compliance-status", params={"framework": "iso_42001"}).json()
    row = next(r for r in rows if r["code"] == "4.3")
    # Still a draft, so not yet current -- but counted, no longer "no coverage".
    assert row["status"] == "partial"
    assert row["tagged_items"][0]["label"] == "Context of the organization"
