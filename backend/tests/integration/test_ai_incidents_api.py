from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.user import User


def create_incident(client: TestClient, **overrides) -> dict:
    payload = {
        "title": "Chatbot gave dosage advice",
        "description": "The support bot recommended a medication dosage to a customer.",
        "detected_on": date.today().isoformat(),
    }
    payload.update(overrides)
    response = client.post("/api/v1/ai-incidents", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_creating_an_incident(client: TestClient, test_user: User) -> None:
    body = create_incident(client, severity="high", owner_id=test_user.id)

    assert body["status"] == "open"
    assert body["severity"] == "high"
    assert body["owner_id"] == test_user.id
    assert body["reporting_deadline"] is None
    assert body["reporting_overdue"] is False
    assert body["corrective_action_ids"] == []
    assert client.get("/api/v1/ai-incidents").json()[0]["id"] == body["id"]


def test_a_serious_incident_without_a_category_is_rejected(
    client: TestClient, test_user: User
) -> None:
    response = client.post(
        "/api/v1/ai-incidents",
        json={
            "title": "t",
            "description": "d",
            "detected_on": date.today().isoformat(),
            "is_serious": True,
        },
    )

    assert response.status_code == 400


def test_an_unreported_serious_incident_past_its_deadline_is_overdue(
    client: TestClient, test_user: User
) -> None:
    detected = date.today() - timedelta(days=3)
    body = create_incident(
        client,
        detected_on=detected.isoformat(),
        is_serious=True,
        serious_category="widespread_or_critical_infrastructure",
    )

    assert body["reporting_deadline"] == (detected + timedelta(days=2)).isoformat()
    assert body["reporting_overdue"] is True

    notified = client.put(
        f"/api/v1/ai-incidents/{body['id']}",
        json={"authority_notified_on": date.today().isoformat(), "authority_reference": "MSA-1"},
    ).json()
    assert notified["reporting_overdue"] is False


def test_resolving_an_unreported_serious_incident_is_refused(
    client: TestClient, test_user: User
) -> None:
    body = create_incident(client, is_serious=True, serious_category="other")

    response = client.put(f"/api/v1/ai-incidents/{body['id']}", json={"status": "resolved"})

    assert response.status_code == 409
    assert client.get(f"/api/v1/ai-incidents/{body['id']}").json()["status"] == "open"


def test_a_corrective_action_raised_from_an_incident_is_linked_back(
    client: TestClient, test_user: User
) -> None:
    incident = create_incident(client)

    corrective_action = client.post(
        "/api/v1/corrective-actions",
        json={
            "title": "Block medical advice in the bot's guardrails",
            "nonconformity_description": incident["description"],
            "source_type": "AIIncident",
            "source_id": incident["id"],
            "assignee_id": test_user.id,
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    ).json()

    body = client.get(f"/api/v1/ai-incidents/{incident['id']}").json()
    assert body["corrective_action_ids"] == [corrective_action["id"]]
    assert client.delete(f"/api/v1/ai-incidents/{incident['id']}").status_code == 409


def test_deleting_an_open_incident(client: TestClient, test_user: User) -> None:
    incident = create_incident(client)

    assert client.delete(f"/api/v1/ai-incidents/{incident['id']}").status_code == 204
    assert client.get(f"/api/v1/ai-incidents/{incident['id']}").status_code == 404


def test_uploading_evidence_to_an_incident(client: TestClient, test_user: User) -> None:
    incident = create_incident(client)

    response = client.post(
        "/api/v1/evidence",
        data={"entity_type": "AIIncident", "entity_id": str(incident["id"])},
        files={"file": ("chat-transcript.pdf", b"file-bytes", "application/pdf")},
    )

    assert response.status_code == 201
    listed = client.get(
        "/api/v1/evidence", params={"entity_type": "AIIncident", "entity_id": incident["id"]}
    ).json()
    assert [item["filename"] for item in listed] == ["chat-transcript.pdf"]
