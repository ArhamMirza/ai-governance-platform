from fastapi.testclient import TestClient


def get_annex_a_control_id(client: TestClient) -> int:
    controls = client.get("/api/v1/framework-controls", params={"framework": "iso_42001"}).json()
    return next(c["id"] for c in controls if c["category"] == "annex_a_control")


def test_get_soa_lists_38_controls_defaulting_to_applicable(client: TestClient) -> None:
    response = client.get("/api/v1/framework-soa")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 38
    assert all(entry["applicability"] == "applicable" for entry in body)
    assert all(entry["justification"] is None for entry in body)


def test_update_soa_entry_persists_applicability_and_justification(client: TestClient) -> None:
    control_id = get_annex_a_control_id(client)

    response = client.put(
        f"/api/v1/framework-soa/{control_id}",
        json={"applicability": "not_applicable", "justification": "Out of scope for us."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["applicability"] == "not_applicable"
    assert body["justification"] == "Out of scope for us."

    reread = client.get("/api/v1/framework-soa").json()
    entry = next(e for e in reread if e["id"] == control_id)
    assert entry["applicability"] == "not_applicable"
    assert entry["justification"] == "Out of scope for us."


def test_update_soa_entry_rejects_invalid_applicability(client: TestClient) -> None:
    control_id = get_annex_a_control_id(client)

    response = client.put(
        f"/api/v1/framework-soa/{control_id}",
        json={"applicability": "maybe", "justification": None},
    )

    assert response.status_code == 400


def test_update_soa_entry_rejects_a_clause_id(client: TestClient) -> None:
    clauses = client.get("/api/v1/framework-controls", params={"framework": "iso_42001"}).json()
    clause_id = next(c["id"] for c in clauses if c["category"] == "clause")

    response = client.put(
        f"/api/v1/framework-soa/{clause_id}",
        json={"applicability": "applicable", "justification": None},
    )

    assert response.status_code == 404


def test_update_soa_entry_is_visible_in_the_audit_log(client: TestClient) -> None:
    control_id = get_annex_a_control_id(client)

    client.put(
        f"/api/v1/framework-soa/{control_id}",
        json={"applicability": "not_applicable", "justification": "Not relevant."},
    )

    response = client.get(
        "/api/v1/audit-log", params={"entity_type": "FrameworkSoaEntry", "entity_id": control_id}
    )
    actions = [entry["action"] for entry in response.json()]
    assert "framework_soa_updated" in actions
