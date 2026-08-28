from fastapi.testclient import TestClient


def get_clause_control_id(client: TestClient) -> int:
    controls = client.get("/api/v1/framework-controls", params={"framework": "iso_42001"}).json()
    return next(c["id"] for c in controls if c["category"] == "clause")


def test_get_mapping_lists_all_clauses_articles_and_annex_a_controls(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/framework-mapping")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 70
    assert {"id", "framework", "code", "title", "category", "tagged_items"} <= body[0].keys()


def test_get_mapping_filtered_by_framework(client: TestClient) -> None:
    response = client.get("/api/v1/framework-mapping", params={"framework": "eu_ai_act"})

    assert response.status_code == 200
    assert len(response.json()) == 8


def test_get_mapping_shows_a_tagged_policy(client: TestClient) -> None:
    policy = client.post("/api/v1/policies", json={"title": "Data Retention Policy"}).json()
    control_id = get_clause_control_id(client)
    client.put(
        "/api/v1/framework-tags",
        params={"entity_type": "Policy", "entity_id": policy["id"]},
        json={"control_ids": [control_id]},
    )

    entries = client.get("/api/v1/framework-mapping").json()
    entry = next(e for e in entries if e["id"] == control_id)
    assert entry["tagged_items"] == [
        {"entity_type": "Policy", "entity_id": policy["id"], "label": "Data Retention Policy"}
    ]


def test_get_mapping_shows_a_tagged_evidence_record(client: TestClient) -> None:
    control_id = get_clause_control_id(client)
    evidence = client.post(
        "/api/v1/evidence",
        data={"entity_type": "Policy", "entity_id": "1"},
        files={"file": ("audit-report.pdf", b"bytes", "application/pdf")},
    ).json()
    client.put(
        "/api/v1/framework-tags",
        params={"entity_type": "Evidence", "entity_id": evidence["id"]},
        json={"control_ids": [control_id]},
    )

    entries = client.get("/api/v1/framework-mapping").json()
    entry = next(e for e in entries if e["id"] == control_id)
    assert entry["tagged_items"] == [
        {"entity_type": "Evidence", "entity_id": evidence["id"], "label": "audit-report.pdf"}
    ]
