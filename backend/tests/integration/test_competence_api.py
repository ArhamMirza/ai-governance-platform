from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.user import User


def create_role(client: TestClient, name: str = "Model Validator") -> int:
    response = client.post(
        "/api/v1/governance-roles",
        json={"name": name, "responsibilities": "Validates models before release"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_requirement(client: TestClient, **overrides) -> dict:
    payload = {"title": "EU AI Act awareness"}
    payload.update(overrides)
    response = client.post("/api/v1/competence/requirements", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_an_everyone_requirement_starts_with_everyone_missing(
    client: TestClient, test_user: User
) -> None:
    requirement = create_requirement(client)

    assert requirement["governance_role_id"] is None
    assert requirement["people"] == [
        {
            "user_id": test_user.id,
            "status": "missing",
            "last_completed_on": None,
            "next_due": None,
        }
    ]
    listed = client.get("/api/v1/competence/requirements").json()
    assert (listed[0]["required_count"], listed[0]["gap_count"]) == (1, 1)


def test_assigning_a_role_puts_the_holder_on_the_hook(client: TestClient, test_user: User) -> None:
    role_id = create_role(client)
    requirement = create_requirement(client, governance_role_id=role_id)
    assert requirement["people"] == []

    client.post(f"/api/v1/governance-roles/{role_id}/assignments", json={"user_id": test_user.id})

    body = client.get(f"/api/v1/competence/requirements/{requirement['id']}").json()
    assert [(p["user_id"], p["status"]) for p in body["people"]] == [(test_user.id, "missing")]


def test_recording_a_completion_makes_the_person_current(
    client: TestClient, test_user: User
) -> None:
    requirement = create_requirement(client, refresh_interval_months=12)
    completed_on = date.today().isoformat()

    response = client.post(
        f"/api/v1/competence/requirements/{requirement['id']}/records",
        json={"user_id": test_user.id, "completed_on": completed_on, "notes": "Online course"},
    )

    assert response.status_code == 201
    body = client.get(f"/api/v1/competence/requirements/{requirement['id']}").json()
    assert body["people"][0]["status"] == "current"
    assert body["people"][0]["last_completed_on"] == completed_on
    assert body["gap_count"] == 0
    assert [record["notes"] for record in body["records"]] == ["Online course"]


def test_a_future_completion_is_refused(client: TestClient, test_user: User) -> None:
    requirement = create_requirement(client)

    response = client.post(
        f"/api/v1/competence/requirements/{requirement['id']}/records",
        json={
            "user_id": test_user.id,
            "completed_on": (date.today() + timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 400


def test_deleting_a_role_a_requirement_targets_is_refused(
    client: TestClient, test_user: User
) -> None:
    role_id = create_role(client)
    create_requirement(client, governance_role_id=role_id)

    assert client.delete(f"/api/v1/governance-roles/{role_id}").status_code == 409


def test_deleting_a_requirement(client: TestClient, test_user: User) -> None:
    requirement = create_requirement(client)

    assert client.delete(f"/api/v1/competence/requirements/{requirement['id']}").status_code == 204
    assert client.get(f"/api/v1/competence/requirements/{requirement['id']}").status_code == 404


def test_uploading_a_certificate_to_a_completion(client: TestClient, test_user: User) -> None:
    requirement = create_requirement(client)
    record = client.post(
        f"/api/v1/competence/requirements/{requirement['id']}/records",
        json={"user_id": test_user.id, "completed_on": date.today().isoformat()},
    ).json()

    response = client.post(
        "/api/v1/evidence",
        data={"entity_type": "CompetenceRecord", "entity_id": str(record["id"])},
        files={"file": ("certificate.pdf", b"file-bytes", "application/pdf")},
    )

    assert response.status_code == 201
    listed = client.get(
        "/api/v1/evidence", params={"entity_type": "CompetenceRecord", "entity_id": record["id"]}
    ).json()
    assert [item["filename"] for item in listed] == ["certificate.pdf"]
