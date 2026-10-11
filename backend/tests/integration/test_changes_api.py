from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.models.user import User

# The server judges "today" in UTC; so do these, so they don't depend on the
# machine's own time zone.
TODAY = datetime.now(UTC).date()


def days(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


def create_change(client: TestClient, **overrides) -> dict:
    payload = {
        "title": "Move the screener to a new base model",
        "change_type": "ai_system",
        "raised_on": days(-30),
        "planned_date": days(30),
    }
    payload.update(overrides)
    response = client.post("/api/v1/changes", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def move(client: TestClient, change_id: int, action: str, note: str | None = None):
    return client.post(f"/api/v1/changes/{change_id}/status", json={"action": action, "note": note})


def create_ai_system(client: TestClient, name: str = "Resume Screener") -> int:
    response = client.post("/api/v1/ai-system-inventory/rows", json={"data": {"name": name}})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_creating_and_listing_changes(client: TestClient, test_user: User) -> None:
    body = create_change(client, owner_id=test_user.id, reason="Vendor deprecates the old model")

    assert body["status"] == "planned"
    assert body["standing"] == {"state": "planned", "overdue": False}
    assert body["owner_id"] == test_user.id
    assert [c["id"] for c in client.get("/api/v1/changes").json()] == [body["id"]]


def test_a_planned_date_before_it_was_raised_is_refused(
    client: TestClient, test_user: User
) -> None:
    response = client.post(
        "/api/v1/changes",
        json={"title": "Backwards", "raised_on": days(-1), "planned_date": days(-5)},
    )

    assert response.status_code == 400


def test_a_change_past_its_planned_date_is_overdue_until_implemented(
    client: TestClient, test_user: User
) -> None:
    change = create_change(client, planned_date=days(-2))
    assert change["standing"]["overdue"] is True

    done = move(client, change["id"], "implement", "Rolled out").json()

    assert done["standing"] == {"state": "implemented", "overdue": False}
    assert (done["closed_on"], done["closure_note"]) == (days(0), "Rolled out")


def test_moving_a_change_on_and_reopening_it(client: TestClient, test_user: User) -> None:
    change = create_change(client)

    started = move(client, change["id"], "start").json()
    assert (started["standing"]["state"], started["started_on"]) == ("in_progress", days(0))
    assert move(client, change["id"], "start").status_code == 409

    move(client, change["id"], "cancel", "Paused")
    reopened = move(client, change["id"], "reopen").json()
    assert (reopened["status"], reopened["closed_on"]) == ("in_progress", None)
    assert move(client, change["id"], "reopen").status_code == 409


def test_standing_as_of_a_past_date(client: TestClient, test_user: User) -> None:
    early = create_change(client, title="Early", planned_date=days(-10))
    move(client, early["id"], "implement")
    create_change(client, title="Set later", raised_on=days(-5), planned_date=days(20))

    then = client.get("/api/v1/changes/standing", params={"as_of": days(-15)}).json()
    assert [(c["title"], c["standing"]["state"], c["standing"]["overdue"]) for c in then] == [
        ("Early", "planned", False)
    ]

    # Eight days ago Early was still open and past its planned date.
    mid = client.get("/api/v1/changes/standing", params={"as_of": days(-8)}).json()
    assert [(c["title"], c["standing"]["overdue"]) for c in mid] == [("Early", True)]

    now = client.get("/api/v1/changes/standing", params={"as_of": days(0)}).json()
    assert {c["title"]: c["standing"]["state"] for c in now} == {
        "Early": "implemented",
        "Set later": "planned",
    }


def test_only_an_untouched_change_can_be_deleted(client: TestClient, test_user: User) -> None:
    started = create_change(client, title="Started")
    move(client, started["id"], "start")
    untouched = create_change(client, title="Untouched")

    assert client.delete(f"/api/v1/changes/{started['id']}").status_code == 409
    assert client.delete(f"/api/v1/changes/{untouched['id']}").status_code == 204
    assert client.get(f"/api/v1/changes/{untouched['id']}").status_code == 404


def test_updating_a_change(client: TestClient, test_user: User) -> None:
    change = create_change(client)

    response = client.put(
        f"/api/v1/changes/{change['id']}",
        json={"consequences": "A week of retraining", "planned_date": days(45)},
    )

    assert response.status_code == 200, response.text
    assert response.json()["consequences"] == "A week of retraining"
    assert response.json()["planned_date"] == days(45)


def test_linking_ai_systems_and_filtering_by_one(client: TestClient, test_user: User) -> None:
    screener = create_ai_system(client)
    chatbot = create_ai_system(client, "Support Chatbot")
    change = create_change(client)
    create_change(client, title="Unlinked")

    response = client.put(
        f"/api/v1/changes/{change['id']}/ai-systems",
        json={"ai_system_row_ids": [screener, chatbot]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["ai_system_row_ids"] == [screener, chatbot]
    listed = client.get("/api/v1/changes", params={"ai_system_row_id": screener}).json()
    assert [c["id"] for c in listed] == [change["id"]]


def test_the_dashboard_flags_overdue_changes_in_their_own_area(
    client: TestClient, test_user: User
) -> None:
    create_change(client, title="Late", planned_date=days(-3))
    create_change(client, title="On time")

    attention = client.get("/api/v1/dashboard/summary").json()["attention"]

    item = next(a for a in attention if a["key"] == "changes_overdue")
    assert (item["count"], item["group"]) == (1, "Management system planning")


def test_an_unknown_change_is_not_found(client: TestClient, test_user: User) -> None:
    assert client.get("/api/v1/changes/999").status_code == 404
    assert move(client, 999, "start").status_code == 404
