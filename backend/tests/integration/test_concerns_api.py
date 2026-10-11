"""Reporting of concerns (A.3.3): employees raise them, handlers act on them.

The anonymity tests look straight at the database -- what an anonymous
concern *doesn't* store is the promise, so that's what's asserted.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLogEntry
from app.models.concern import Concern
from app.models.user import User, UserRole
from app.services import ai_system_lifecycle_service, concern_service

TODAY = datetime.now(UTC).date()
DESCRIPTION = "The screening tool keeps ranking candidates from one university first."


@pytest.fixture(autouse=True)
def _fresh_lookup_limits():
    concern_service.reset_lookup_limits()
    yield
    concern_service.reset_lookup_limits()


@pytest.fixture()
def employee(make_user: Callable[..., User]) -> User:
    return make_user(role=UserRole.EMPLOYEE, name="Elena Employee", email="elena@example.com")


def submit(client: TestClient, **overrides):
    payload = {"category": "bias_or_fairness", "description": DESCRIPTION, "anonymous": False}
    payload.update(overrides)
    return client.post("/api/v1/staff/concerns", json=payload)


def make_ai_system(client: TestClient, name: str = "Resume Screener") -> int:
    response = client.post("/api/v1/ai-system-inventory/rows", json={"data": {"name": name}})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def days_ago(n: int) -> str:
    return (TODAY - timedelta(days=n)).isoformat()


def log_by_phone(client: TestClient, **overrides) -> dict:
    payload = {
        "category": "safety_or_harm",
        "description": "A manager says the chatbot gave a customer unsafe advice.",
        "channel": "phone",
    }
    payload.update(overrides)
    response = client.post("/api/v1/concerns", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---------- raising a concern ----------


def test_an_employee_can_raise_a_named_concern_and_sees_it_listed(
    client: TestClient, login_as, employee: User
) -> None:
    login_as(employee)

    response = submit(client)

    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["tracking_code"].replace("-", "")) == 12
    assert body["concern"]["status"] == "received"
    assert body["concern"]["is_anonymous"] is False
    mine = client.get("/api/v1/staff/concerns/mine").json()
    assert [c["id"] for c in mine] == [body["concern"]["id"]]


def test_an_anonymous_concern_keeps_nothing_that_identifies_the_reporter(
    client: TestClient, login_as, employee: User, db_session: Session
) -> None:
    login_as(employee)

    body = submit(client, anonymous=True).json()

    concern = db_session.get(Concern, body["concern"]["id"])
    assert concern.reporter_id is None
    assert concern.is_anonymous is True
    # No reporter id, name or email in any column of the row.
    stored = " ".join(str(getattr(concern, column.key)) for column in inspect(Concern).columns)
    assert str(employee.id) not in stored.split()
    assert employee.name not in stored
    assert employee.email not in stored
    # Receiving it wasn't audit-logged: that entry's actor and timestamp would
    # tie it to this person's session.
    assert db_session.query(AuditLogEntry).filter_by(entity_type="Concern").count() == 0
    # And a concern is dated, not timestamped.
    assert not [c for c in inspect(Concern).columns if "DATETIME" in str(c.type).upper()]


def test_a_named_concern_is_recorded_against_its_reporter_and_audit_logged(
    client: TestClient, login_as, employee: User, db_session: Session
) -> None:
    login_as(employee)

    body = submit(client).json()

    concern = db_session.get(Concern, body["concern"]["id"])
    assert concern.reporter_id == employee.id
    entry = db_session.query(AuditLogEntry).filter_by(entity_type="Concern").one()
    assert (entry.action, entry.actor_id) == ("received", employee.id)


def test_the_tracking_code_itself_is_never_stored(
    client: TestClient, login_as, employee: User, db_session: Session
) -> None:
    login_as(employee)

    body = submit(client, anonymous=True).json()

    code = body["tracking_code"].replace("-", "")
    concern = db_session.get(Concern, body["concern"]["id"])
    stored = " ".join(str(getattr(concern, column.key)) for column in inspect(Concern).columns)
    assert code not in stored
    assert len(concern.tracking_code_hash) == 64


@pytest.mark.parametrize("transform", [lambda c: c, str.lower, lambda c: c.replace("-", " ")])
def test_the_tracking_code_finds_the_concern_however_it_is_typed(
    client: TestClient, login_as, employee: User, transform
) -> None:
    login_as(employee)
    body = submit(client, anonymous=True).json()

    response = client.post(
        "/api/v1/staff/concerns/lookup", json={"tracking_code": transform(body["tracking_code"])}
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == body["concern"]["id"]


def test_an_anonymous_concern_isnt_listed_under_my_concerns(
    client: TestClient, login_as, employee: User
) -> None:
    login_as(employee)
    submit(client, anonymous=True)

    assert client.get("/api/v1/staff/concerns/mine").json() == []


def test_a_concern_is_for_its_reporter_alone(
    client: TestClient, login_as, employee: User, make_user: Callable[..., User]
) -> None:
    login_as(employee)
    submit(client)
    colleague = make_user(role=UserRole.EMPLOYEE, email="colleague@example.com")
    login_as(colleague)

    assert client.get("/api/v1/staff/concerns/mine").json() == []


def test_a_wrong_or_malformed_code_is_just_not_found(
    client: TestClient, login_as, employee: User
) -> None:
    login_as(employee)
    submit(client, anonymous=True)

    for code in ("ABCD-EFGH-JKMN", "not a code", "ABCD"):
        response = client.post("/api/v1/staff/concerns/lookup", json={"tracking_code": code})
        assert response.status_code == 404, code


def test_guessing_codes_locks_the_guesser_out_even_for_the_right_one(
    client: TestClient, login_as, employee: User, make_user: Callable[..., User]
) -> None:
    login_as(employee)
    code = submit(client, anonymous=True).json()["tracking_code"]
    guesser = make_user(role=UserRole.EMPLOYEE, email="guesser@example.com")
    login_as(guesser)

    for _ in range(5):
        assert (
            client.post(
                "/api/v1/staff/concerns/lookup", json={"tracking_code": "ABCD-EFGH-JKMN"}
            ).status_code
            == 404
        )
    locked = client.post("/api/v1/staff/concerns/lookup", json={"tracking_code": code})

    assert locked.status_code == 429
    # Someone else, asking with the genuine code, is unaffected.
    login_as(employee)
    assert (
        client.post("/api/v1/staff/concerns/lookup", json={"tracking_code": code}).status_code
        == 200
    )


def test_a_concern_needs_enough_words_to_be_useful(
    client: TestClient, login_as, employee: User
) -> None:
    login_as(employee)

    assert submit(client, description="too short").status_code == 422


def test_a_concern_can_name_one_ai_system_or_say_it_is_not_sure(
    client: TestClient, login_as, employee: User, test_user: User
) -> None:
    row_id = make_ai_system(client)
    login_as(employee)

    named = submit(client, ai_system_row_id=row_id)
    unsure = submit(client, system_note="Something on the HR portal, I'm not sure what")

    assert named.status_code == 201 and unsure.status_code == 201
    assert submit(client, ai_system_row_id=99999).status_code == 404


def test_an_archived_system_cant_be_reported_against_through_the_portal(
    client: TestClient, login_as, employee: User, db_session: Session
) -> None:
    row_id = make_ai_system(client)
    lifecycle = ai_system_lifecycle_service.get_or_create(db_session, row_id)
    lifecycle.archived_at = datetime.now(UTC)
    db_session.commit()
    login_as(employee)

    assert submit(client, ai_system_row_id=row_id).status_code == 404
    assert client.get("/api/v1/staff/ai-systems").json() == []


def test_employees_choose_a_system_from_names_and_ids_only(
    client: TestClient, login_as, employee: User, test_user: User
) -> None:
    make_ai_system(client, "Resume Screener")
    make_ai_system(client, "Chatbot")
    login_as(employee)

    systems = client.get("/api/v1/staff/ai-systems").json()

    assert [s["name"] for s in systems] == ["Chatbot", "Resume Screener"]
    assert all(set(s) == {"id", "name"} for s in systems)


# ---------- who can handle them ----------


HANDLER_ROUTES = [
    ("GET", "/api/v1/concerns"),
    ("GET", "/api/v1/concerns/1"),
    ("POST", "/api/v1/concerns"),
    ("PUT", "/api/v1/concerns/1"),
    ("POST", "/api/v1/concerns/1/status"),
    ("POST", "/api/v1/concerns/1/raise-incident"),
    ("GET", "/api/v1/concerns/1/corrective-actions"),
    ("GET", "/api/v1/concerns/settings"),
    ("PUT", "/api/v1/concerns/settings"),
]


@pytest.mark.parametrize("role", [UserRole.CONTRIBUTOR, UserRole.VIEWER, UserRole.EMPLOYEE])
def test_nobody_but_a_handler_can_reach_the_register(
    client: TestClient, login_as, make_user: Callable[..., User], role: UserRole
) -> None:
    login_as(make_user(role=role))

    for method, path in HANDLER_ROUTES:
        response = client.request(method, path, json={} if method != "GET" else None)
        assert response.status_code == 403, (role, method, path)


def test_only_administrators_handle_concerns_and_that_includes_the_caigo(
    client: TestClient,
    login_as,
    make_user: Callable[..., User],
    caigo_admin: User,
) -> None:
    """The Chief AI Governance Officer must be an admin account, so they're
    covered by the admin rule -- but a contributor, however senior, isn't."""
    admin = make_user(role=UserRole.ADMIN)
    contributor = make_user(role=UserRole.CONTRIBUTOR)

    for user, expected in ((admin, True), (caigo_admin, True), (contributor, False)):
        login_as(user)
        assert client.get("/api/v1/concerns/access").json() == {"can_handle": expected}
        assert client.get("/api/v1/concerns").status_code == (200 if expected else 403)


# ---------- handling one ----------


def test_the_register_shows_who_raised_a_named_concern_but_not_an_anonymous_one(
    client: TestClient, login_as, employee: User, test_user: User
) -> None:
    login_as(employee)
    named = submit(client).json()["concern"]["id"]
    anonymous = submit(client, anonymous=True).json()["concern"]["id"]
    login_as(test_user)

    register = {c["id"]: c for c in client.get("/api/v1/concerns").json()}

    assert register[named]["reporter_name"] == "Elena Employee"
    assert register[anonymous]["reporter_name"] is None
    assert register[anonymous]["reporter_id"] is None


def test_triage_moves_a_concern_through_review_to_a_close(
    client: TestClient, login_as, employee: User, test_user: User
) -> None:
    login_as(employee)
    concern_id = submit(client).json()["concern"]["id"]
    login_as(test_user)

    reviewing = client.post(f"/api/v1/concerns/{concern_id}/status", json={"action": "acknowledge"})
    assert reviewing.status_code == 200, reviewing.text
    assert reviewing.json()["status"] == "under_review"
    assert reviewing.json()["acknowledged_on"] == TODAY.isoformat()
    assert reviewing.json()["handler_id"] == test_user.id

    resolved = client.post(
        f"/api/v1/concerns/{concern_id}/status",
        json={"action": "resolve", "outcome": "substantiated", "note": "Re-ranked; audit added"},
    ).json()
    assert (resolved["status"], resolved["outcome"], resolved["closed_on"]) == (
        "resolved",
        "substantiated",
        TODAY.isoformat(),
    )

    reopened = client.post(
        f"/api/v1/concerns/{concern_id}/status", json={"action": "reopen"}
    ).json()
    assert (reopened["status"], reopened["outcome"], reopened["closed_on"]) == (
        "under_review",
        None,
        None,
    )


def test_resolving_needs_an_outcome_and_dismissing_needs_a_reason(
    client: TestClient, login_as, employee: User, test_user: User
) -> None:
    login_as(employee)
    concern_id = submit(client).json()["concern"]["id"]
    login_as(test_user)
    url = f"/api/v1/concerns/{concern_id}/status"

    assert client.post(url, json={"action": "resolve"}).status_code == 400
    assert client.post(url, json={"action": "dismiss", "note": "   "}).status_code == 400

    dismissed = client.post(url, json={"action": "dismiss", "note": "Outside our scope"}).json()
    assert (dismissed["status"], dismissed["closure_note"]) == ("not_actioned", "Outside our scope")
    # A dismissed concern was still seen: acknowledged the day it closed.
    assert dismissed["acknowledged_on"] == TODAY.isoformat()


def test_impossible_moves_are_refused(
    client: TestClient, login_as, employee: User, test_user: User
) -> None:
    login_as(employee)
    concern_id = submit(client).json()["concern"]["id"]
    login_as(test_user)
    url = f"/api/v1/concerns/{concern_id}/status"

    assert client.post(url, json={"action": "reopen"}).status_code == 409  # Not closed.
    client.post(url, json={"action": "acknowledge"})
    assert client.post(url, json={"action": "acknowledge"}).status_code == 409  # Already.
    client.post(url, json={"action": "dismiss", "note": "Duplicate"})
    assert client.post(url, json={"action": "resolve", "outcome": "no_finding"}).status_code == 409


def test_the_reporter_sees_the_reply_and_outcome_but_never_the_internal_notes(
    client: TestClient, login_as, employee: User, test_user: User
) -> None:
    login_as(employee)
    code = submit(client, anonymous=True).json()["tracking_code"]
    login_as(test_user)
    concern_id = client.get("/api/v1/concerns").json()[0]["id"]
    client.put(
        f"/api/v1/concerns/{concern_id}",
        json={
            "internal_notes": "Likely the HR vendor's model -- raise with their account manager",
            "reply_to_reporter": "Thank you. We've asked for the ranking logic and will re-test.",
        },
    )
    client.post(
        f"/api/v1/concerns/{concern_id}/status",
        json={"action": "resolve", "outcome": "partly_substantiated", "note": "Internal closing"},
    )
    login_as(employee)

    seen = client.post("/api/v1/staff/concerns/lookup", json={"tracking_code": code}).json()

    assert seen["reply_to_reporter"].startswith("Thank you")
    assert (seen["status"], seen["outcome"]) == ("resolved", "partly_substantiated")
    # An allowlist: nothing a handler wrote privately, nor who the handler is.
    assert set(seen) == {
        "id",
        "category",
        "description",
        "received_on",
        "status",
        "acknowledged_on",
        "closed_on",
        "outcome",
        "reply_to_reporter",
        "is_anonymous",
    }
    assert "HR vendor" not in str(seen)
    assert "Internal closing" not in str(seen)


def test_what_a_handler_wrote_is_not_copied_into_the_audit_log(
    client: TestClient, login_as, employee: User, test_user: User, db_session: Session
) -> None:
    login_as(employee)
    concern_id = submit(client).json()["concern"]["id"]
    login_as(test_user)

    client.put(
        f"/api/v1/concerns/{concern_id}",
        json={"internal_notes": "SECRET-NOTE about Dana", "reply_to_reporter": "SECRET-REPLY"},
    )

    updated = (
        db_session.query(AuditLogEntry)
        .filter_by(entity_type="Concern", entity_id=concern_id, action="updated")
        .one()
    )
    assert updated.diff == {"fields": ["internal_notes", "reply_to_reporter"]}
    assert "SECRET" not in str(updated.diff)


def test_a_concern_goes_overdue_for_acknowledgement_only_after_the_window(
    client: TestClient, login_as, test_user: User
) -> None:
    in_window = log_by_phone(client, received_on=days_ago(7))
    late = log_by_phone(client, received_on=days_ago(8))

    by_id = {c["id"]: c for c in client.get("/api/v1/concerns").json()}

    assert by_id[in_window["id"]]["awaiting_triage"] is False
    assert by_id[late["id"]]["awaiting_triage"] is True
    assert by_id[late["id"]]["acknowledge_by"] == days_ago(1)

    client.post(f"/api/v1/concerns/{late['id']}/status", json={"action": "acknowledge"})
    assert client.get(f"/api/v1/concerns/{late['id']}").json()["awaiting_triage"] is False


def test_the_acknowledgement_window_is_set_in_the_settings(
    client: TestClient, login_as, test_user: User
) -> None:
    concern = log_by_phone(client, received_on=days_ago(4))
    assert client.get(f"/api/v1/concerns/{concern['id']}").json()["awaiting_triage"] is False

    client.put("/api/v1/concerns/settings", json={"acknowledge_within_days": 3})

    assert client.get(f"/api/v1/concerns/{concern['id']}").json()["awaiting_triage"] is True


def test_raising_an_incident_links_it_without_saying_who_raised_the_concern(
    client: TestClient, login_as, employee: User, test_user: User
) -> None:
    row_id = make_ai_system(client)
    login_as(employee)
    concern_id = submit(client, ai_system_row_id=row_id).json()["concern"]["id"]
    login_as(test_user)

    raised = client.post(f"/api/v1/concerns/{concern_id}/raise-incident")

    assert raised.status_code == 200, raised.text
    incident = client.get(f"/api/v1/ai-incidents/{raised.json()['incident_id']}").json()
    assert incident["description"] == DESCRIPTION
    assert incident["ai_system_row_id"] == row_id
    assert employee.name not in str(incident)
    # Raising it counts as picking it up.
    assert (raised.json()["status"], raised.json()["acknowledged_on"]) == (
        "under_review",
        TODAY.isoformat(),
    )
    assert client.post(f"/api/v1/concerns/{concern_id}/raise-incident").status_code == 409


def test_a_corrective_action_can_be_raised_from_a_concern_and_is_listed_on_it(
    client: TestClient, login_as, employee: User, test_user: User
) -> None:
    login_as(employee)
    concern_id = submit(client).json()["concern"]["id"]
    login_as(test_user)

    created = client.post(
        f"/api/v1/concerns/{concern_id}/corrective-actions",
        json={
            "title": "Audit the ranking for university bias",
            "assignee_id": test_user.id,
            "due_date": (TODAY + timedelta(days=30)).isoformat(),
        },
    )

    assert created.status_code == 201, created.text
    assert (created.json()["source_type"], created.json()["source_id"]) == ("Concern", concern_id)
    listed = client.get(f"/api/v1/concerns/{concern_id}/corrective-actions").json()
    assert [a["title"] for a in listed] == ["Audit the ranking for university bias"]


def test_a_handler_can_record_a_concern_raised_by_phone(
    client: TestClient, login_as, test_user: User
) -> None:
    body = log_by_phone(client, reporter_note="Priya, support team, happy to be contacted")

    assert (body["channel"], body["is_anonymous"], body["status"]) == ("phone", False, "received")
    assert body["reporter_note"] == "Priya, support team, happy to be contacted"
    assert body["reporter_id"] is None


def test_a_concern_logged_as_anonymous_drops_the_reporter_note(
    client: TestClient, login_as, test_user: User
) -> None:
    body = log_by_phone(client, anonymous=True, reporter_note="Priya from support")

    assert (body["is_anonymous"], body["reporter_note"]) == (True, None)


def test_the_employee_home_is_not_a_channel_a_handler_logs_for_someone(
    client: TestClient, login_as, test_user: User
) -> None:
    response = client.post(
        "/api/v1/concerns",
        json={"description": "Raised for them", "channel": "employee_portal"},
    )

    assert response.status_code == 400
    future = client.post(
        "/api/v1/concerns",
        json={
            "description": "Dated ahead",
            "channel": "email",
            "received_on": (TODAY + timedelta(days=1)).isoformat(),
        },
    )
    assert future.status_code == 400


def test_deleting_an_ai_system_unlinks_the_concern_but_keeps_what_it_was_called(
    client: TestClient, login_as, employee: User, test_user: User
) -> None:
    row_id = make_ai_system(client, "Old Screener")
    login_as(employee)
    concern_id = submit(client, ai_system_row_id=row_id).json()["concern"]["id"]
    login_as(test_user)

    assert client.delete(f"/api/v1/ai-system-inventory/rows/{row_id}").status_code == 204

    concern = client.get(f"/api/v1/concerns/{concern_id}").json()
    assert concern["ai_system_row_id"] is None
    assert concern["system_note"] == "Old Screener (since deleted)"
    assert concern["description"] == DESCRIPTION


# ---------- settings, the dashboard and compliance ----------


def test_the_process_description_reaches_employees(
    client: TestClient, login_as, employee: User, test_user: User
) -> None:
    saved = client.put(
        "/api/v1/concerns/settings",
        json={
            "process_description": "Tell us here, or call 555-0100.",
            "acknowledge_within_days": 5,
        },
    )
    assert saved.status_code == 200, saved.text
    login_as(employee)

    process = client.get("/api/v1/staff/concerns-process").json()

    assert process == {
        "process_description": "Tell us here, or call 555-0100.",
        "acknowledge_within_days": 5,
    }


def test_the_acknowledgement_window_is_bounded(
    client: TestClient, login_as, test_user: User
) -> None:
    assert (
        client.put("/api/v1/concerns/settings", json={"acknowledge_within_days": 0}).status_code
        == 422
    )
    assert (
        client.put("/api/v1/concerns/settings", json={"acknowledge_within_days": 91}).status_code
        == 422
    )


def test_the_dashboard_counts_concerns_nobody_has_acknowledged_in_time(
    client: TestClient, login_as, test_user: User
) -> None:
    log_by_phone(client, received_on=days_ago(10))
    log_by_phone(client, received_on=days_ago(1))
    acknowledged = log_by_phone(client, received_on=days_ago(12))
    client.post(f"/api/v1/concerns/{acknowledged['id']}/status", json={"action": "acknowledge"})

    attention = client.get("/api/v1/dashboard/summary").json()["attention"]

    item = next(a for a in attention if a["key"] == "concerns_awaiting_triage")
    assert (item["count"], item["group"], item["severity"]) == (
        1,
        "Incidents & corrective actions",
        "danger",
    )


def test_the_reporting_process_counts_toward_a_clause_only_while_it_works(
    client: TestClient, login_as, test_user: User
) -> None:
    settings = client.get("/api/v1/concerns/settings").json()
    clause = next(
        c["id"]
        for c in client.get("/api/v1/framework-controls", params={"framework": "iso_42001"}).json()
        if c["code"] == "A.3.3"
    )
    client.put(
        "/api/v1/framework-tags",
        params={"entity_type": "ConcernSettings", "entity_id": settings["id"]},
        json={"control_ids": [clause]},
    )

    def status() -> tuple[str, str]:
        rows = client.get("/api/v1/compliance-status", params={"framework": "iso_42001"}).json()
        row = next(r for r in rows if r["code"] == "A.3.3")
        return row["status"], row["tagged_items"][0]["detail"]

    assert status() == ("partial", "How to report a concern hasn't been described to staff")

    client.put("/api/v1/concerns/settings", json={"process_description": "Use the staff home."})
    assert status()[0] == "satisfied"

    late = log_by_phone(client, received_on=days_ago(9))
    state, detail = status()
    assert state == "partial"
    assert detail == "1 concern(s) not acknowledged within 7 days"

    client.post(f"/api/v1/concerns/{late['id']}/status", json={"action": "acknowledge"})
    assert status()[0] == "satisfied"


def test_a_settings_row_is_not_created_by_merely_reading_the_dashboard(
    client: TestClient, test_user: User, db_session: Session
) -> None:
    from app.models.concern import ConcernSettings

    client.get("/api/v1/dashboard/summary")

    assert db_session.query(ConcernSettings).count() == 0
