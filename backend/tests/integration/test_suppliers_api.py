from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.user import User
from tests.helpers import complete_impact_assessment_db


def create_supplier(client: TestClient, **overrides) -> dict:
    payload = {"name": "Acme Models", "supplier_type": "model_provider"}
    payload.update(overrides)
    response = client.post("/api/v1/suppliers", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_ai_system(client: TestClient, name: str = "Resume Screener") -> int:
    response = client.post("/api/v1/ai-system-inventory/rows", json={"data": {"name": name}})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_creating_a_supplier(client: TestClient, test_user: User) -> None:
    body = create_supplier(client, owner_id=test_user.id, contract_reference="MSA-2026-01")

    assert body["status"] == "active"
    assert body["owner_id"] == test_user.id
    assert body["ai_system_row_ids"] == []
    assert body["reviews"] == []
    assert [s["id"] for s in client.get("/api/v1/suppliers").json()] == [body["id"]]


def test_half_a_review_schedule_is_refused(client: TestClient, test_user: User) -> None:
    response = client.post("/api/v1/suppliers", json={"name": "Acme", "review_interval_months": 12})

    assert response.status_code == 400


def test_a_contract_ending_soon_is_flagged(client: TestClient, test_user: User) -> None:
    body = create_supplier(client, contract_end=(date.today() + timedelta(days=10)).isoformat())

    assert body["contract_status"] == "expiring"

    ended = client.put(f"/api/v1/suppliers/{body['id']}", json={"status": "inactive"}).json()
    assert ended["contract_status"] is None


def test_recording_a_review_clears_an_overdue_one(client: TestClient, test_user: User) -> None:
    body = create_supplier(
        client,
        review_interval_months=12,
        first_review_due=(date.today() - timedelta(days=1)).isoformat(),
    )
    assert body["review_overdue"] is True

    response = client.post(
        f"/api/v1/suppliers/{body['id']}/reviews",
        json={"review_date": date.today().isoformat(), "outcome": "satisfactory"},
    )
    assert response.status_code == 201

    detail = client.get(f"/api/v1/suppliers/{body['id']}").json()
    assert detail["review_overdue"] is False
    assert [review["outcome"] for review in detail["reviews"]] == ["satisfactory"]

    review_id = detail["reviews"][0]["id"]
    assert client.delete(f"/api/v1/suppliers/reviews/{review_id}").status_code == 204
    assert client.get(f"/api/v1/suppliers/{body['id']}").json()["review_overdue"] is True


def test_linking_ai_systems_and_filtering_by_one(client: TestClient, test_user: User) -> None:
    screener = create_ai_system(client)
    other = create_ai_system(client, "Fraud Model")
    linked = create_supplier(client)
    create_supplier(client, name="Unrelated Co")

    response = client.put(
        f"/api/v1/suppliers/{linked['id']}/ai-systems", json={"ai_system_row_ids": [screener]}
    )

    assert response.status_code == 200
    assert response.json()["ai_system_row_ids"] == [screener]
    filtered = client.get("/api/v1/suppliers", params={"ai_system_row_id": screener}).json()
    assert [s["id"] for s in filtered] == [linked["id"]]
    assert client.get("/api/v1/suppliers", params={"ai_system_row_id": other}).json() == []


def test_deleting_a_supplier(client: TestClient, test_user: User) -> None:
    body = create_supplier(client)

    assert client.delete(f"/api/v1/suppliers/{body['id']}").status_code == 204
    assert client.get(f"/api/v1/suppliers/{body['id']}").status_code == 404


def test_uploading_a_contract_and_review_evidence(client: TestClient, test_user: User) -> None:
    supplier = create_supplier(client)
    review = client.post(
        f"/api/v1/suppliers/{supplier['id']}/reviews",
        json={"review_date": date.today().isoformat()},
    ).json()

    for entity_type, entity_id, filename in [
        ("Supplier", supplier["id"], "msa.pdf"),
        ("SupplierReview", review["id"], "soc2.pdf"),
    ]:
        response = client.post(
            "/api/v1/evidence",
            data={"entity_type": entity_type, "entity_id": str(entity_id)},
            files={"file": (filename, b"file-bytes", "application/pdf")},
        )
        assert response.status_code == 201
        listed = client.get(
            "/api/v1/evidence", params={"entity_type": entity_type, "entity_id": entity_id}
        ).json()
        assert [item["filename"] for item in listed] == [filename]


def test_recording_a_suppliers_role_and_art25_triggers(client: TestClient, test_user: User) -> None:
    screener = create_ai_system(client)
    supplier = create_supplier(client)
    client.put(
        f"/api/v1/suppliers/{supplier['id']}/ai-systems", json={"ai_system_row_ids": [screener]}
    )

    response = client.put(
        f"/api/v1/suppliers/{supplier['id']}/ai-systems/{screener}",
        json={"supplier_role": "provider", "rebranded": True},
    )

    assert response.status_code == 200
    [link] = response.json()["ai_system_links"]
    assert link == {
        "ai_system_row_id": screener,
        "supplier_role": "provider",
        "rebranded": True,
        "substantially_modified": False,
        "repurposed_to_high_risk": False,
        "art25_triggered": True,
    }
    attention = client.get("/api/v1/dashboard/summary").json()["attention"]
    assert any(a["key"] == "art25_possible_provider" and a["count"] == 1 for a in attention)

    # The same link, seen from the AI system's side.
    listed = client.get("/api/v1/suppliers", params={"ai_system_row_id": screener}).json()
    assert listed[0]["ai_system_links"][0]["art25_triggered"] is True


def test_updating_an_unlinked_ai_system_is_a_404(client: TestClient, test_user: User) -> None:
    supplier = create_supplier(client)

    response = client.put(
        f"/api/v1/suppliers/{supplier['id']}/ai-systems/{create_ai_system(client)}",
        json={"supplier_role": "provider"},
    )

    assert response.status_code == 404


def test_a_supplier_lists_the_risk_items_naming_it(
    client: TestClient, test_user: User, db_session
) -> None:
    supplier = create_supplier(client)
    row_id = create_ai_system(client)
    complete_impact_assessment_db(db_session, row_id)
    assessment = client.post("/api/v1/risk-assessments", json={"ai_system_row_id": row_id}).json()
    columns = [
        c["key"]
        for c in client.get(f"/api/v1/risk-assessments/{assessment['id']}/sheet").json()["columns"]
    ]
    assert columns[columns.index("risk_owner") + 1] == "supplier_id"
    client.post(
        f"/api/v1/risk-assessments/{assessment['id']}/rows",
        json={"data": {"category": "Third party", "supplier_id": str(supplier["id"])}},
    )

    items = client.get(f"/api/v1/suppliers/{supplier['id']}/risk-items").json()

    assert [(i["risk_assessment_id"], i["category"]) for i in items] == [
        (assessment["id"], "Third party")
    ]
