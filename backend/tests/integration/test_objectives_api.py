from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.models.user import User

# The server judges "today" in UTC; so do these, so they don't depend on the
# machine's own time zone.
TODAY = datetime.now(UTC).date()


def days(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


def create_measured(client: TestClient, **overrides) -> dict:
    payload = {
        "title": "Bias test pass rate",
        "kind": "measured",
        "established_on": days(-200),
        "target_date": days(200),
        "metric_name": "Pass rate",
        "unit": "%",
        "direction": "at_least",
        "target_value": 95,
        "measurement_interval_months": 3,
        "first_measurement_due": days(30),
    }
    payload.update(overrides)
    response = client.post("/api/v1/objectives", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_milestone(client: TestClient, **overrides) -> dict:
    payload = {
        "title": "Publish an AI transparency notice",
        "kind": "milestone",
        "established_on": days(-200),
        "target_date": days(60),
    }
    payload.update(overrides)
    response = client.post("/api/v1/objectives", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def record(client: TestClient, objective_id: int, offset: int, value: float) -> dict:
    response = client.post(
        f"/api/v1/objectives/{objective_id}/measurements",
        json={"measured_on": days(offset), "value": value},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_ai_system(client: TestClient, name: str = "Resume Screener") -> int:
    response = client.post("/api/v1/ai-system-inventory/rows", json={"data": {"name": name}})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_creating_and_listing_objectives(client: TestClient, test_user: User) -> None:
    body = create_measured(client, owner_id=test_user.id)

    assert body["status"] == "active"
    assert body["standing"]["state"] == "not_measured"
    assert body["standing"]["next_measurement_due"] == days(30)
    assert body["measurements"] == []
    assert [o["id"] for o in client.get("/api/v1/objectives").json()] == [body["id"]]


def test_an_incomplete_measured_objective_is_refused(client: TestClient, test_user: User) -> None:
    response = client.post("/api/v1/objectives", json={"title": "Pass rate", "kind": "measured"})

    assert response.status_code == 400


def test_readings_update_the_standing_newest_first(client: TestClient, test_user: User) -> None:
    objective = create_measured(client)
    record(client, objective["id"], -60, 90)
    record(client, objective["id"], -5, 97)

    body = client.get(f"/api/v1/objectives/{objective['id']}").json()

    assert body["standing"]["state"] == "on_track"
    assert body["standing"]["latest_value"] == 97
    assert [m["value"] for m in body["measurements"]] == [97, 90]
    assert body["measurements"][0]["recorded_by"] == test_user.id


def test_deleting_a_reading(client: TestClient, test_user: User) -> None:
    objective = create_measured(client)
    first = record(client, objective["id"], -60, 90)
    record(client, objective["id"], -5, 97)

    response = client.delete(f"/api/v1/objectives/measurements/{first['id']}")

    assert response.status_code == 204
    body = client.get(f"/api/v1/objectives/{objective['id']}").json()
    assert [m["value"] for m in body["measurements"]] == [97]


def test_standing_as_of_a_past_date(client: TestClient, test_user: User) -> None:
    objective = create_measured(client)
    record(client, objective["id"], -60, 90)
    record(client, objective["id"], -5, 97)
    create_milestone(client, title="Set later", established_on=days(-10))

    then = client.get("/api/v1/objectives/standing", params={"as_of": days(-30)}).json()

    assert [(o["title"], o["standing"]["state"], o["standing"]["latest_value"]) for o in then] == [
        ("Bias test pass rate", "off_track", 90)
    ]
    now = client.get("/api/v1/objectives/standing", params={"as_of": days(0)}).json()
    assert {o["title"]: o["standing"]["state"] for o in now} == {
        "Bias test pass rate": "on_track",
        "Set later": "in_progress",
    }


def test_closing_and_reopening(client: TestClient, test_user: User) -> None:
    objective = create_milestone(client)

    closed = client.post(
        f"/api/v1/objectives/{objective['id']}/close",
        json={"status": "achieved", "closure_note": "Published on the website"},
    )

    assert closed.status_code == 200, closed.text
    assert closed.json()["standing"]["state"] == "achieved"
    assert closed.json()["closed_on"] == days(0)
    again = client.post(f"/api/v1/objectives/{objective['id']}/close", json={"status": "withdrawn"})
    assert again.status_code == 409

    reopened = client.post(f"/api/v1/objectives/{objective['id']}/reopen")
    assert reopened.json()["standing"]["state"] == "in_progress"


def test_a_closed_objective_refuses_readings(client: TestClient, test_user: User) -> None:
    objective = create_measured(client)
    client.post(f"/api/v1/objectives/{objective['id']}/close", json={"status": "withdrawn"})

    response = client.post(
        f"/api/v1/objectives/{objective['id']}/measurements",
        json={"measured_on": days(0), "value": 96},
    )

    assert response.status_code == 409


def test_an_objective_with_readings_cant_be_deleted(client: TestClient, test_user: User) -> None:
    objective = create_measured(client)
    record(client, objective["id"], -5, 97)

    assert client.delete(f"/api/v1/objectives/{objective['id']}").status_code == 409

    milestone = create_milestone(client)
    assert client.delete(f"/api/v1/objectives/{milestone['id']}").status_code == 204
    assert client.get(f"/api/v1/objectives/{milestone['id']}").status_code == 404


def test_updating_an_objective(client: TestClient, test_user: User) -> None:
    objective = create_measured(client)

    response = client.put(
        f"/api/v1/objectives/{objective['id']}",
        json={"target_value": 98, "planned_actions": "Add a fairness gate to CI"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["target_value"] == 98
    assert response.json()["planned_actions"] == "Add a fairness gate to CI"


def test_linking_ai_systems_and_filtering_by_one(client: TestClient, test_user: User) -> None:
    screener = create_ai_system(client)
    chatbot = create_ai_system(client, "Support Chatbot")
    objective = create_measured(client)
    create_milestone(client)

    response = client.put(
        f"/api/v1/objectives/{objective['id']}/ai-systems",
        json={"ai_system_row_ids": [screener, chatbot]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["ai_system_row_ids"] == [screener, chatbot]
    listed = client.get("/api/v1/objectives", params={"ai_system_row_id": screener}).json()
    assert [o["id"] for o in listed] == [objective["id"]]
    assert listed[0]["ai_system_row_ids"] == [screener, chatbot]


def test_an_unknown_objective_is_not_found(client: TestClient, test_user: User) -> None:
    assert client.get("/api/v1/objectives/999").status_code == 404
    assert client.delete("/api/v1/objectives/measurements/999").status_code == 404
