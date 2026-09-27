from fastapi.testclient import TestClient


def get_annex_a_control_id(client: TestClient) -> int:
    controls = client.get("/api/v1/framework-controls", params={"framework": "iso_42001"}).json()
    return next(c["id"] for c in controls if c["category"] == "annex_a_control")


def test_get_status_lists_every_control_starting_uncovered(client: TestClient) -> None:
    response = client.get("/api/v1/compliance-status")

    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    assert all(entry["status"] == "no_coverage" for entry in body)
    assert all(entry["tagged_items"] == [] for entry in body)


def test_get_status_can_be_filtered_by_framework(client: TestClient) -> None:
    response = client.get("/api/v1/compliance-status", params={"framework": "eu_ai_act"})

    body = response.json()
    assert len(body) > 0
    assert all(entry["framework"] == "eu_ai_act" for entry in body)


def test_marking_an_annex_a_control_not_applicable_is_reflected_in_status(
    client: TestClient,
) -> None:
    control_id = get_annex_a_control_id(client)
    client.put(
        f"/api/v1/framework-soa/{control_id}",
        json={"applicability": "not_applicable", "justification": "Out of scope."},
    )

    body = client.get("/api/v1/compliance-status").json()
    entry = next(e for e in body if e["id"] == control_id)

    assert entry["status"] == "not_applicable"
    assert entry["reason"] == "Out of scope."


def test_get_summary_counts_every_control_exactly_once(client: TestClient) -> None:
    all_controls = client.get("/api/v1/framework-controls").json()
    iso_clauses = [
        c for c in all_controls if c["framework"] == "iso_42001" and c["category"] == "clause"
    ]
    annex_a = [
        c
        for c in all_controls
        if c["framework"] == "iso_42001" and c["category"] == "annex_a_control"
    ]
    eu_ai_act = [c for c in all_controls if c["framework"] == "eu_ai_act"]

    summary = client.get("/api/v1/compliance-status/summary").json()

    for key, controls in (
        ("iso_42001_clauses", iso_clauses),
        ("iso_42001_annex_a", annex_a),
        ("eu_ai_act", eu_ai_act),
    ):
        counts = summary[key]
        total = (
            counts["satisfied"]
            + counts["partial"]
            + counts["no_coverage"]
            + counts["not_applicable"]
        )
        assert total == len(controls), key
