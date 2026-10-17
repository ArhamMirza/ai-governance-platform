from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.models.user import User, UserRole

# The server judges "today" in UTC; so do these, so they don't depend on the
# machine's own time zone.
TODAY = datetime.now(UTC).date()


def days(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


def create_improvement(client: TestClient, **overrides) -> dict:
    payload = {
        "title": "Add a fairness check to every model release",
        "source": "idea",
        "raised_on": days(-30),
        "target_date": days(30),
    }
    payload.update(overrides)
    response = client.post("/api/v1/improvements", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def move(client: TestClient, improvement_id: int, action: str, note: str | None = None):
    return client.post(
        f"/api/v1/improvements/{improvement_id}/status", json={"action": action, "note": note}
    )


def create_observation(client: TestClient) -> int:
    program = client.post(
        "/api/v1/audit-programs", json={"title": "AIMS audits", "schedule_type": "ad_hoc"}
    ).json()
    audit = client.post(
        f"/api/v1/audit-programs/{program['id']}/audits",
        json={"title": "Q1 Audit", "planned_date": days(0)},
    ).json()
    finding = client.post(
        f"/api/v1/audit-programs/{program['id']}/audits/{audit['id']}/findings",
        json={"description": "Release checklists vary by team.", "finding_type": "observation"},
    )
    assert finding.status_code == 201, finding.text
    return finding.json()["id"]


def log_concern(client: TestClient) -> int:
    response = client.post(
        "/api/v1/concerns",
        json={
            "category": "safety_or_harm",
            "description": "A manager says the chatbot gave a customer unsafe advice.",
            "channel": "phone",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


# ---------- recording ----------


def test_creating_and_listing_improvements(client: TestClient, test_user: User) -> None:
    body = create_improvement(client, owner_id=test_user.id, expected_benefit="Fewer surprises")

    assert body["status"] == "proposed"
    assert body["standing"] == {"state": "proposed", "overdue": False}
    assert (body["source"], body["source_label"]) == ("idea", None)
    assert body["expected_benefit"] == "Fewer surprises"
    assert [i["id"] for i in client.get("/api/v1/improvements").json()] == [body["id"]]


def test_raised_on_defaults_to_today(client: TestClient, test_user: User) -> None:
    body = create_improvement(client, raised_on=None)

    assert body["raised_on"] == days(0)


def test_a_target_before_it_was_raised_is_refused(client: TestClient, test_user: User) -> None:
    response = client.post(
        "/api/v1/improvements",
        json={"title": "Backwards", "raised_on": days(-1), "target_date": days(-5)},
    )

    assert response.status_code == 400


def test_updating_an_improvement_but_not_blanking_its_dates(
    client: TestClient, test_user: User
) -> None:
    improvement = create_improvement(client)
    url = f"/api/v1/improvements/{improvement['id']}"

    response = client.put(url, json={"description": "Every team, every release"})
    assert response.status_code == 200, response.text
    assert response.json()["description"] == "Every team, every release"

    assert client.put(url, json={"target_date": None}).status_code == 400
    assert client.put(url, json={"target_date": days(-60)}).status_code == 400
    assert client.get(url).json()["target_date"] == days(30)


# ---------- where it came from ----------


def test_raising_one_from_an_audit_observation_names_the_audit(
    client: TestClient, test_user: User
) -> None:
    finding_id = create_observation(client)

    body = create_improvement(
        client, source="other", source_type="AuditFinding", source_id=finding_id
    )

    # The category follows the record, whatever was sent.
    assert body["source"] == "internal_audit"
    assert body["source_label"] == "Finding in Q1 Audit"
    listed = client.get(
        "/api/v1/improvements", params={"source_type": "AuditFinding", "source_id": finding_id}
    ).json()
    assert [i["id"] for i in listed] == [body["id"]]


def test_one_raised_from_a_concern_carries_nothing_of_what_was_reported(
    client: TestClient, test_user: User
) -> None:
    concern_id = log_concern(client)

    body = create_improvement(client, source_type="Concern", source_id=concern_id)

    assert body["source"] == "concern"
    assert body["source_label"] == f"Concern #{concern_id}"
    assert "unsafe advice" not in str(body)


def test_a_source_that_doesnt_exist_or_is_half_given_is_refused(
    client: TestClient, test_user: User
) -> None:
    payload = {"title": "Orphan", "target_date": days(10)}

    missing = client.post(
        "/api/v1/improvements", json={**payload, "source_type": "Concern", "source_id": 999}
    )
    half = client.post("/api/v1/improvements", json={**payload, "source_id": 1})
    unknown = client.post(
        "/api/v1/improvements", json={**payload, "source_type": "Policy", "source_id": 1}
    )

    assert missing.status_code == 404
    assert half.status_code == 400
    assert unknown.status_code == 422


# ---------- moving it on ----------


def test_accepting_then_implementing_records_what_came_of_it(
    client: TestClient, test_user: User
) -> None:
    improvement = create_improvement(client)

    accepted = move(client, improvement["id"], "accept").json()
    assert (accepted["standing"]["state"], accepted["decided_on"]) == ("accepted", days(0))
    assert move(client, improvement["id"], "accept").status_code == 409

    done = move(client, improvement["id"], "implement", "  Checklist adopted by all teams  ")
    assert done.status_code == 200, done.text
    body = done.json()
    assert body["standing"] == {"state": "implemented", "overdue": False}
    assert (body["closed_on"], body["outcome"]) == (days(0), "Checklist adopted by all teams")


def test_implementing_needs_an_outcome_and_an_accepted_improvement(
    client: TestClient, test_user: User
) -> None:
    improvement = create_improvement(client)

    assert move(client, improvement["id"], "implement", "Done").status_code == 409
    move(client, improvement["id"], "accept")
    assert move(client, improvement["id"], "implement").status_code == 400
    assert move(client, improvement["id"], "implement", "   ").status_code == 400


def test_declining_needs_a_reason_and_still_counts_as_decided(
    client: TestClient, test_user: User
) -> None:
    improvement = create_improvement(client)

    assert move(client, improvement["id"], "decline").status_code == 400
    declined = move(client, improvement["id"], "decline", "Covered by the new SDLC").json()

    assert declined["standing"] == {"state": "declined", "overdue": False}
    assert declined["decline_reason"] == "Covered by the new SDLC"
    assert move(client, improvement["id"], "decline", "Again").status_code == 409


def test_reopening_puts_it_back_where_it_was_and_clears_the_closure(
    client: TestClient, test_user: User
) -> None:
    proposed = create_improvement(client)
    move(client, proposed["id"], "decline", "Not now")
    accepted = create_improvement(client, title="Accepted first")
    move(client, accepted["id"], "accept")
    move(client, accepted["id"], "implement", "Did it")

    back_to_proposed = move(client, proposed["id"], "reopen").json()
    back_to_accepted = move(client, accepted["id"], "reopen").json()

    assert (back_to_proposed["status"], back_to_proposed["decline_reason"]) == ("proposed", None)
    assert (back_to_accepted["status"], back_to_accepted["outcome"]) == ("accepted", None)
    assert back_to_accepted["closed_on"] is None
    assert move(client, accepted["id"], "reopen").status_code == 409


def test_an_open_improvement_past_its_target_is_overdue_until_closed(
    client: TestClient, test_user: User
) -> None:
    improvement = create_improvement(client, target_date=days(-1))
    assert improvement["standing"]["overdue"] is True

    move(client, improvement["id"], "accept")
    done = move(client, improvement["id"], "implement", "Done late").json()

    assert done["standing"]["overdue"] is False


def test_only_an_undecided_improvement_can_be_deleted(client: TestClient, test_user: User) -> None:
    untouched = create_improvement(client)
    accepted = create_improvement(client, title="Accepted")
    move(client, accepted["id"], "accept")

    assert client.delete(f"/api/v1/improvements/{accepted['id']}").status_code == 409
    assert client.delete(f"/api/v1/improvements/{untouched['id']}").status_code == 204
    assert client.get(f"/api/v1/improvements/{untouched['id']}").status_code == 404


# ---------- carrying it out as a change ----------


def test_an_accepted_improvement_is_carried_out_as_a_planned_change(
    client: TestClient, test_user: User
) -> None:
    improvement = create_improvement(
        client,
        description="One checklist for every release",
        expected_benefit="Fewer surprises in production",
        owner_id=test_user.id,
    )
    url = f"/api/v1/improvements/{improvement['id']}/carry-out-as-change"
    assert client.post(url).status_code == 409  # Not accepted yet.
    move(client, improvement["id"], "accept")

    response = client.post(url)

    assert response.status_code == 200, response.text
    change_id = response.json()["change_id"]
    change = client.get(f"/api/v1/changes/{change_id}").json()
    assert change["title"] == improvement["title"]
    assert change["reason"] == "Fewer surprises in production"
    assert (change["raised_on"], change["planned_date"]) == (days(0), days(30))
    assert change["owner_id"] == test_user.id
    assert client.post(url).status_code == 409  # Only once.


def test_a_change_for_an_improvement_already_past_its_target_is_planned_for_today(
    client: TestClient, test_user: User
) -> None:
    improvement = create_improvement(client, target_date=days(-5))
    move(client, improvement["id"], "accept")

    body = client.post(f"/api/v1/improvements/{improvement['id']}/carry-out-as-change").json()

    assert client.get(f"/api/v1/changes/{body['change_id']}").json()["planned_date"] == days(0)


def test_deleting_the_change_leaves_the_improvement_unlinked(
    client: TestClient, test_user: User
) -> None:
    improvement = create_improvement(client)
    move(client, improvement["id"], "accept")
    change_id = client.post(f"/api/v1/improvements/{improvement['id']}/carry-out-as-change").json()[
        "change_id"
    ]

    assert client.delete(f"/api/v1/changes/{change_id}").status_code == 204

    assert client.get(f"/api/v1/improvements/{improvement['id']}").json()["change_id"] is None


# ---------- management review, dashboard, compliance ----------


def test_a_management_review_sees_improvements_as_they_stood_on_its_date(
    client: TestClient, test_user: User
) -> None:
    earlier = create_improvement(client, title="Raised early", raised_on=days(-20))
    create_improvement(client, title="Raised later", raised_on=days(-2))
    move(client, earlier["id"], "accept")

    on_the_day = client.get("/api/v1/improvements/standing", params={"as_of": days(-10)}).json()

    assert [(i["title"], i["standing"]["state"]) for i in on_the_day] == [
        ("Raised early", "proposed")
    ]


def test_the_dashboard_flags_overdue_improvements_in_the_planning_area(
    client: TestClient, test_user: User
) -> None:
    create_improvement(client, title="Late", target_date=days(-3))
    create_improvement(client, title="On time")

    attention = client.get("/api/v1/dashboard/summary").json()["attention"]

    item = next(a for a in attention if a["key"] == "improvements_overdue")
    assert (item["count"], item["group"]) == (1, "Management system planning")


def test_an_improvement_tagged_to_10_1_counts_unless_overdue(
    client: TestClient, test_user: User
) -> None:
    controls = client.get("/api/v1/framework-controls", params={"framework": "iso_42001"}).json()
    clause = next(c for c in controls if c["code"] == "10.1")
    on_time = create_improvement(client, title="On time")
    late = create_improvement(client, title="Late", target_date=days(-1))
    for improvement in (on_time, late):
        response = client.put(
            "/api/v1/framework-tags",
            params={"entity_type": "Improvement", "entity_id": improvement["id"]},
            json={"control_ids": [clause["id"]]},
        )
        assert response.status_code == 200, response.text

    status = next(
        row
        for row in client.get("/api/v1/compliance-status", params={"framework": "iso_42001"}).json()
        if row["code"] == "10.1"
    )

    assert status["status"] == "partial"
    details = {item["label"]: item["detail"] for item in status["tagged_items"]}
    assert details == {
        "On time": f"Improvement proposed, target {days(30)}",
        "Late": f"Improvement overdue since {days(-1)}",
    }


# ---------- access ----------


def test_viewers_can_read_but_not_record(
    client: TestClient,
    test_user: User,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
) -> None:
    improvement = create_improvement(client)
    login_as(make_user(role=UserRole.VIEWER))

    assert client.get(f"/api/v1/improvements/{improvement['id']}").status_code == 200
    assert (
        client.post(
            "/api/v1/improvements", json={"title": "Nope", "target_date": days(1)}
        ).status_code
        == 403
    )
    assert move(client, improvement["id"], "accept").status_code == 403


def test_an_unknown_improvement_is_not_found(client: TestClient, test_user: User) -> None:
    assert client.get("/api/v1/improvements/999").status_code == 404
    assert move(client, 999, "accept").status_code == 404
