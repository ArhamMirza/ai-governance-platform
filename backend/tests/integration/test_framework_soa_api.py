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


def test_a_never_reviewed_control_has_no_review_date(client: TestClient) -> None:
    """Defaulting this to "now" made every untouched control read as though
    somebody had just assessed it."""
    body = client.get("/api/v1/framework-soa").json()

    assert all(entry["updated_at"] is None for entry in body)


def test_recording_a_decision_stamps_the_review_date(client: TestClient) -> None:
    control_id = get_annex_a_control_id(client)

    client.put(
        f"/api/v1/framework-soa/{control_id}",
        json={"applicability": "applicable", "justification": "In scope."},
    )

    entry = next(e for e in client.get("/api/v1/framework-soa").json() if e["id"] == control_id)
    assert entry["updated_at"] is not None


def test_excluding_a_control_requires_a_justification(client: TestClient) -> None:
    """ISO 42001 expects the SoA to say why a control is excluded."""
    control_id = get_annex_a_control_id(client)

    response = client.put(
        f"/api/v1/framework-soa/{control_id}",
        json={"applicability": "not_applicable", "justification": None},
    )

    assert response.status_code == 400
    assert "justification" in response.json()["detail"]


def test_a_blank_justification_does_not_count_as_one(client: TestClient) -> None:
    control_id = get_annex_a_control_id(client)

    response = client.put(
        f"/api/v1/framework-soa/{control_id}",
        json={"applicability": "not_applicable", "justification": "   "},
    )

    assert response.status_code == 400


def test_an_applicable_control_needs_no_justification(client: TestClient) -> None:
    control_id = get_annex_a_control_id(client)

    response = client.put(
        f"/api/v1/framework-soa/{control_id}",
        json={"applicability": "applicable", "justification": None},
    )

    assert response.status_code == 200


def test_a_deleted_document_stops_counting_as_coverage(client: TestClient) -> None:
    """The SoA is read as evidence that a control is covered, so a tag whose
    document has been deleted must not keep showing up there."""
    control_id = get_annex_a_control_id(client)
    policy = client.post("/api/v1/policies", json={"title": "Data Retention Policy"}).json()
    evidence = client.post(
        "/api/v1/evidence",
        data={"entity_type": "Policy", "entity_id": str(policy["id"])},
        files={"file": ("retention.pdf", b"bytes", "application/pdf")},
    ).json()
    client.put(
        "/api/v1/framework-tags",
        params={"entity_type": "Evidence", "entity_id": evidence["id"]},
        json={"control_ids": [control_id]},
    )
    entry = next(e for e in client.get("/api/v1/framework-soa").json() if e["id"] == control_id)
    assert [item["label"] for item in entry["tagged_items"]] == ["retention.pdf"]

    client.delete(f"/api/v1/evidence/{evidence['id']}")

    entry = next(e for e in client.get("/api/v1/framework-soa").json() if e["id"] == control_id)
    assert entry["tagged_items"] == []


def test_the_mapping_view_drops_it_too(client: TestClient) -> None:
    control_id = get_annex_a_control_id(client)
    policy = client.post("/api/v1/policies", json={"title": "Data Retention Policy"}).json()
    evidence = client.post(
        "/api/v1/evidence",
        data={"entity_type": "Policy", "entity_id": str(policy["id"])},
        files={"file": ("retention.pdf", b"bytes", "application/pdf")},
    ).json()
    client.put(
        "/api/v1/framework-tags",
        params={"entity_type": "Evidence", "entity_id": evidence["id"]},
        json={"control_ids": [control_id]},
    )

    client.delete(f"/api/v1/evidence/{evidence['id']}")

    mapping = client.get("/api/v1/framework-mapping").json()
    entry = next(e for e in mapping if e["id"] == control_id)
    assert entry["tagged_items"] == []
