from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.models.user import User

# The server judges "today" in UTC; so do these, so they don't depend on the
# machine's own time zone.
TODAY = datetime.now(UTC).date()


def days(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


def create_item(client: TestClient, **overrides) -> dict:
    payload = {
        "topic": "Quarterly AI governance update",
        "audience": "Leadership team",
        "direction": "internal",
        "method": "Board pack",
        "interval_months": 3,
        "first_due": days(30),
    }
    payload.update(overrides)
    response = client.post("/api/v1/communications", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def record(client: TestClient, item_id: int, offset: int, summary: str | None = None):
    return client.post(
        f"/api/v1/communications/{item_id}/records",
        json={"communicated_on": days(offset), "summary": summary},
    )


def test_creating_and_listing_planned_communications(client: TestClient, test_user: User) -> None:
    body = create_item(client, responsible_id=test_user.id)

    assert body["status"] == "active"
    assert body["responsible_id"] == test_user.id
    assert (body["next_due"], body["overdue"], body["last_communicated_on"]) == (
        days(30),
        False,
        None,
    )
    assert body["records"] == []
    assert [i["id"] for i in client.get("/api/v1/communications").json()] == [body["id"]]


def test_half_a_schedule_is_refused(client: TestClient, test_user: User) -> None:
    response = client.post(
        "/api/v1/communications",
        json={"topic": "Update", "audience": "Staff", "interval_months": 3},
    )

    assert response.status_code == 400


def test_an_item_with_no_schedule_is_never_due(client: TestClient, test_user: User) -> None:
    body = create_item(
        client,
        topic="Notify customers of an incident",
        audience="Affected customers",
        direction="external",
        interval_months=None,
        first_due=None,
    )

    assert (body["next_due"], body["overdue"]) == (None, False)


def test_a_missed_first_date_is_overdue_until_it_is_done(
    client: TestClient, test_user: User
) -> None:
    item = create_item(client, first_due=days(-5))
    assert item["overdue"] is True

    assert record(client, item["id"], 0, "Presented").status_code == 201

    body = client.get(f"/api/v1/communications/{item['id']}").json()
    assert body["overdue"] is False
    assert body["last_communicated_on"] == days(0)
    assert [r["summary"] for r in body["records"]] == ["Presented"]
    assert body["records"][0]["recorded_by"] == test_user.id


def test_records_are_listed_newest_first(client: TestClient, test_user: User) -> None:
    item = create_item(client)
    record(client, item["id"], -60, "Old")
    record(client, item["id"], -10, "Recent")

    body = client.get(f"/api/v1/communications/{item['id']}").json()

    assert [r["summary"] for r in body["records"]] == ["Recent", "Old"]


def test_a_communication_cant_be_dated_in_the_future(client: TestClient, test_user: User) -> None:
    item = create_item(client)

    assert record(client, item["id"], 1).status_code == 400


def test_deleting_a_record_makes_it_overdue_again(client: TestClient, test_user: User) -> None:
    item = create_item(client, first_due=days(-5))
    made = record(client, item["id"], 0).json()

    response = client.delete(f"/api/v1/communications/records/{made['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/v1/communications/{item['id']}").json()["overdue"] is True


def test_retiring_an_item_stops_it_being_overdue(client: TestClient, test_user: User) -> None:
    item = create_item(client, first_due=days(-5))

    response = client.put(f"/api/v1/communications/{item['id']}", json={"status": "retired"})

    assert response.status_code == 200, response.text
    assert (response.json()["status"], response.json()["overdue"]) == ("retired", False)


def test_updating_an_item_and_deleting_it(client: TestClient, test_user: User) -> None:
    item = create_item(client)

    updated = client.put(
        f"/api/v1/communications/{item['id']}",
        json={"audience": "Board and leadership", "method": "Slides"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["audience"] == "Board and leadership"

    assert client.delete(f"/api/v1/communications/{item['id']}").status_code == 204
    assert client.get(f"/api/v1/communications/{item['id']}").status_code == 404


def test_the_dashboard_counts_overdue_communications_in_the_planning_area(
    client: TestClient, test_user: User
) -> None:
    create_item(client, topic="Late", first_due=days(-3))
    create_item(client, topic="On time")

    attention = client.get("/api/v1/dashboard/summary").json()["attention"]

    item = next(a for a in attention if a["key"] == "communications_overdue")
    assert (item["count"], item["group"]) == (1, "Management system planning")


def test_an_unknown_item_or_record_is_not_found(client: TestClient, test_user: User) -> None:
    assert client.get("/api/v1/communications/999").status_code == 404
    assert client.delete("/api/v1/communications/records/999").status_code == 404
    assert record(client, 999, 0).status_code == 404
