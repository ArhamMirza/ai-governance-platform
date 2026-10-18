from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.models.user import User, UserRole
from app.services import ai_tool_service, ai_usage_service

# The server judges "today" in UTC; so do these, so they don't depend on the
# machine's own time zone.
TODAY = datetime.now(UTC).date()


def days(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


@pytest.fixture(autouse=True)
def _fresh_key_limits():
    ai_usage_service.reset_key_limits()
    yield
    ai_usage_service.reset_key_limits()


@pytest.fixture()
def catalogue(db_session):
    """ChatGPT and Claude, as the migration would have catalogued them."""
    ai_tool_service.install_default_catalog(db_session)


def make_rule(client: TestClient, **overrides) -> dict:
    payload = {
        "name": "Payment card numbers",
        "kind": "builtin",
        "builtin_key": "credit_card",
        "classification": "confidential",
        "action": "block",
    }
    payload.update(overrides)
    response = client.post("/api/v1/dlp-rules", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def issue_key(client: TestClient) -> str:
    response = client.post("/api/v1/ai-use/enrollment-key")
    assert response.status_code == 201, response.text
    return response.json()["key"]


def bearer(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


def event(**overrides) -> dict:
    payload = {
        "day": days(0),
        "domain": "chatgpt.com",
        "event_type": "unapproved_site",
        "action": "monitored",
        "count": 1,
    }
    payload.update(overrides)
    return payload


def send(client: TestClient, key: str, events: list[dict], email: str = "elena@example.com"):
    return client.post(
        "/api/v1/agent/events",
        headers=bearer(key),
        json={"user_email": email, "events": events},
    )


# ---------- DLP rules ----------


def test_a_builtin_rule_keeps_only_its_detector(client: TestClient, test_user: User) -> None:
    rule = make_rule(client, keywords=["ignored"], pattern="ignored")

    assert (rule["builtin_key"], rule["keywords"], rule["pattern"]) == ("credit_card", None, None)
    assert (rule["classification"], rule["action"], rule["enabled"]) == (
        "confidential",
        "block",
        True,
    )
    assert [r["id"] for r in client.get("/api/v1/dlp-rules").json()] == [rule["id"]]


def test_a_keyword_rule_and_a_pattern_rule_are_checked_for_their_kind(
    client: TestClient, test_user: User
) -> None:
    keywords = make_rule(
        client,
        name="Client names",
        kind="keywords",
        builtin_key=None,
        keywords=[" Acme Corp ", "acme corp", "Project Falcon"],
        action="warn",
    )
    pattern = make_rule(
        client,
        name="Ticket numbers",
        kind="regex",
        builtin_key=None,
        pattern=r"\bPROJ-\d{4}\b",
        classification="internal",
    )

    assert keywords["keywords"] == ["Acme Corp", "Project Falcon"]
    assert pattern["pattern"] == r"\bPROJ-\d{4}\b"


@pytest.mark.parametrize(
    "overrides",
    [
        {"builtin_key": "nonsense"},
        {"builtin_key": None},
        {"kind": "keywords", "keywords": []},
        {"kind": "keywords", "keywords": ["ab"]},
        {"kind": "regex", "pattern": "(a+)+"},
        {"kind": "regex", "pattern": "a*"},
        {"kind": "regex", "pattern": None},
    ],
)
def test_a_rule_that_couldnt_run_safely_is_refused(
    client: TestClient, test_user: User, overrides: dict
) -> None:
    payload = {
        "name": "Bad",
        "kind": "builtin",
        "builtin_key": "credit_card",
        "classification": "internal",
        **overrides,
    }

    assert client.post("/api/v1/dlp-rules", json=payload).status_code == 400


def test_the_built_in_detectors_are_listed_with_what_they_catch(
    client: TestClient, test_user: User
) -> None:
    detectors = client.get("/api/v1/dlp-rules/detectors").json()

    keys = {d["key"] for d in detectors}
    assert {"credit_card", "api_key", "private_key", "pk_cnic", "iban"} <= keys
    assert all(d["label"] and d["description"] for d in detectors)


def test_updating_a_rule_checks_its_definition_but_not_its_kind(
    client: TestClient, test_user: User
) -> None:
    rule = make_rule(client)
    url = f"/api/v1/dlp-rules/{rule['id']}"

    assert client.put(url, json={"action": "warn", "enabled": False}).status_code == 200
    changed = client.get(url).json()
    assert (changed["action"], changed["enabled"]) == ("warn", False)
    assert client.put(url, json={"builtin_key": "iban"}).json()["builtin_key"] == "iban"
    assert client.put(url, json={"builtin_key": "nonsense"}).status_code == 400
    assert client.put(url, json={"name": None}).status_code == 400
    assert client.put(url, json={"enabled": None}).status_code == 400
    # A keyword list sent to a builtin rule is ignored: its kind decides what it uses.
    assert client.put(url, json={"keywords": ["whatever"]}).status_code == 200
    assert client.get(url).json()["keywords"] is None


def test_editing_a_keyword_rule_revalidates_the_list(client: TestClient, test_user: User) -> None:
    rule = make_rule(client, kind="keywords", builtin_key=None, keywords=["Falcon"])
    url = f"/api/v1/dlp-rules/{rule['id']}"

    assert client.put(url, json={"keywords": ["Falcon", "Osprey"]}).json()["keywords"] == [
        "Falcon",
        "Osprey",
    ]
    assert client.put(url, json={"keywords": []}).status_code == 400
    assert client.get(url).json()["keywords"] == ["Falcon", "Osprey"]


def test_a_rule_can_be_deleted_and_its_audit_entry_names_it_not_its_definition(
    client: TestClient, test_user: User
) -> None:
    rule = make_rule(
        client, name="Client names", kind="keywords", builtin_key=None, keywords=["Acme Corp"]
    )

    assert client.delete(f"/api/v1/dlp-rules/{rule['id']}").status_code == 204
    assert client.get(f"/api/v1/dlp-rules/{rule['id']}").status_code == 404
    log = client.get(
        "/api/v1/audit-log", params={"entity_type": "DLPRule", "entity_id": rule["id"]}
    ).json()
    assert {entry["action"] for entry in log} == {"created", "deleted"}
    assert "Acme" not in str(log)


def test_viewers_can_read_the_rules_but_not_change_them(
    client: TestClient, test_user: User, login_as, make_user
) -> None:
    rule = make_rule(client)
    login_as(make_user(role=UserRole.VIEWER))

    assert client.get(f"/api/v1/dlp-rules/{rule['id']}").status_code == 200
    assert client.delete(f"/api/v1/dlp-rules/{rule['id']}").status_code == 403
    payload = {"name": "X", "kind": "builtin", "builtin_key": "iban", "classification": "internal"}
    assert client.post("/api/v1/dlp-rules", json=payload).status_code == 403


# ---------- settings and the enrollment key ----------


def test_settings_start_at_their_defaults_and_can_be_changed(
    client: TestClient, test_user: User
) -> None:
    initial = client.get("/api/v1/ai-use/settings").json()

    assert (initial["unapproved_site_action"], initial["retention_days"]) == ("block", 90)
    assert (initial["enrollment_key_issued"], initial["staff_notice"]) == (False, None)
    changed = client.put(
        "/api/v1/ai-use/settings",
        json={
            "unapproved_site_action": "warn",
            "retention_days": 30,
            "staff_notice": "  We count visits to AI sites. We never read what you type.  ",
        },
    ).json()
    assert (changed["unapproved_site_action"], changed["retention_days"]) == ("warn", 30)
    assert changed["staff_notice"] == "We count visits to AI sites. We never read what you type."


def test_settings_refuse_nonsense(client: TestClient, test_user: User) -> None:
    url = "/api/v1/ai-use/settings"

    assert client.put(url, json={"retention_days": 3}).status_code == 422
    assert client.put(url, json={"retention_days": 5000}).status_code == 422
    assert client.put(url, json={"unapproved_site_action": "shrug"}).status_code == 422
    assert client.put(url, json={"retention_days": None}).status_code == 400


def test_the_notice_text_stays_out_of_the_audit_trail(client: TestClient, test_user: User) -> None:
    client.put("/api/v1/ai-use/settings", json={"staff_notice": "Secret wording"})
    settings = client.get("/api/v1/ai-use/settings").json()

    log = client.get(
        "/api/v1/audit-log", params={"entity_type": "AIUseSettings", "entity_id": settings["id"]}
    ).json()

    assert [e["action"] for e in log] == ["updated"]
    assert "Secret wording" not in str(log)


@pytest.mark.parametrize("role", [UserRole.CONTRIBUTOR, UserRole.VIEWER, UserRole.EMPLOYEE])
def test_only_an_administrator_manages_ai_use(
    client: TestClient, login_as, make_user, role: UserRole
) -> None:
    login_as(make_user(role=role))

    for method, path in (
        ("GET", "/api/v1/ai-use/settings"),
        ("PUT", "/api/v1/ai-use/settings"),
        ("POST", "/api/v1/ai-use/enrollment-key"),
        ("GET", "/api/v1/ai-use/usage"),
    ):
        response = client.request(method, path, json={} if method != "GET" else None)
        assert response.status_code == 403, (role, method, path)


def test_the_key_is_shown_once_and_only_its_hash_is_kept(
    client: TestClient, db_session, test_user: User
) -> None:
    response = client.post("/api/v1/ai-use/enrollment-key")

    key = response.json()["key"]
    assert response.status_code == 201
    assert key.startswith("aigk_") and response.json()["hint"] == key[-4:]
    settings = client.get("/api/v1/ai-use/settings").json()
    assert settings["enrollment_key_issued"] is True
    assert settings["enrollment_key_hint"] == key[-4:]
    assert settings["enrollment_key_created_on"] == days(0)
    assert key not in str(settings)
    from app.repositories import ai_use_repository

    stored = ai_use_repository.get_settings(db_session)
    assert stored.enrollment_key_hash != key and len(stored.enrollment_key_hash) == 64
    log = client.get(
        "/api/v1/audit-log", params={"entity_type": "AIUseSettings", "entity_id": settings["id"]}
    ).json()
    assert key not in str(log)


def test_a_new_key_revokes_the_old_one(client: TestClient, test_user: User) -> None:
    old = issue_key(client)
    assert client.get("/api/v1/agent/policy", headers=bearer(old)).status_code == 200

    new = issue_key(client)

    assert new != old
    assert client.get("/api/v1/agent/policy", headers=bearer(old)).status_code == 401
    assert client.get("/api/v1/agent/policy", headers=bearer(new)).status_code == 200


# ---------- the policy the extension reads ----------


def test_the_policy_needs_the_key_and_a_session_is_no_substitute(
    client: TestClient, test_user: User
) -> None:
    key = issue_key(client)

    # `client` is signed in as an administrator, and still needs the key.
    assert client.get("/api/v1/agent/policy").status_code == 401
    assert client.get("/api/v1/agent/policy", headers=bearer("aigk_wrong")).status_code == 401
    assert client.get("/api/v1/agent/policy", headers={"Authorization": key}).status_code == 401
    assert client.get("/api/v1/agent/policy", headers=bearer(key)).status_code == 200


def test_with_no_key_issued_nothing_gets_in(client: TestClient, test_user: User) -> None:
    assert client.get("/api/v1/agent/policy", headers=bearer("")).status_code == 401
    assert client.get("/api/v1/agent/policy", headers=bearer("aigk_anything")).status_code == 401


def test_the_key_opens_the_agent_routes_and_nothing_else(
    client: TestClient, test_user: User
) -> None:
    from app.dependencies import get_current_user
    from app.main import app

    key = issue_key(client)
    # From here on there is no signed-in user: only the key.
    app.dependency_overrides.pop(get_current_user)

    for path in (
        "/api/v1/policies",
        "/api/v1/ai-tools",
        "/api/v1/dlp-rules",
        "/api/v1/ai-use/usage",
    ):
        assert client.get(path, headers=bearer(key)).status_code == 401, path
    assert client.get("/api/v1/agent/policy", headers=bearer(key)).status_code == 200


def test_guessing_keys_locks_the_guesser_out_even_for_the_right_one(
    client: TestClient, test_user: User
) -> None:
    key = issue_key(client)

    statuses = [
        client.get("/api/v1/agent/policy", headers=bearer(f"aigk_guess{i}")).status_code
        for i in range(10)
    ]
    locked = client.get("/api/v1/agent/policy", headers=bearer(key))

    assert statuses == [401] * 10
    assert locked.status_code == 429


def test_a_successful_call_doesnt_count_against_the_caller(
    client: TestClient, test_user: User
) -> None:
    key = issue_key(client)

    assert all(
        client.get("/api/v1/agent/policy", headers=bearer(key)).status_code == 200
        for _ in range(30)
    )


def test_the_policy_lists_every_tool_and_only_the_enabled_rules(
    client: TestClient, test_user: User, caigo_admin: User, login_as, catalogue
) -> None:
    key = issue_key(client)
    live = make_rule(client, name="Live", action="block")
    make_rule(client, name="Switched off", enabled=False)
    login_as(caigo_admin)
    tools = {t["name"]: t for t in client.get("/api/v1/ai-tools").json()}
    client.post(
        f"/api/v1/ai-tools/{tools['Claude']['id']}/decision",
        json={"action": "restrict", "max_data_classification": "internal"},
    )
    login_as(test_user)
    client.put(
        "/api/v1/ai-use/settings",
        json={"unapproved_site_action": "warn", "staff_notice": "We count visits."},
    )

    policy = client.get("/api/v1/agent/policy", headers=bearer(key)).json()

    assert (policy["unapproved_site_action"], policy["staff_notice"]) == (
        "warn",
        "We count visits.",
    )
    assert [r["id"] for r in policy["rules"]] == [live["id"]]
    assert set(policy["rules"][0]) == {
        "id",
        "name",
        "kind",
        "builtin_key",
        "keywords",
        "pattern",
        "classification",
        "action",
    }
    listed = {t["name"]: t for t in policy["tools"]}
    assert len(listed) == 12
    assert listed["Claude"] == {
        "name": "Claude",
        "domains": ["claude.ai"],
        "status": "restricted",
        "max_data_classification": "internal",
    }
    assert listed["ChatGPT"]["status"] == "catalogued"


def test_the_policy_carries_a_tag_that_changes_only_when_the_policy_does(
    client: TestClient, test_user: User, catalogue
) -> None:
    key = issue_key(client)

    first = client.get("/api/v1/agent/policy", headers=bearer(key))
    etag = first.headers["etag"]
    unchanged = client.get("/api/v1/agent/policy", headers={**bearer(key), "If-None-Match": etag})
    make_rule(client)
    changed = client.get("/api/v1/agent/policy", headers={**bearer(key), "If-None-Match": etag})

    assert etag.startswith('"') and etag.endswith('"')
    assert unchanged.status_code == 304 and unchanged.content == b""
    assert changed.status_code == 200 and changed.headers["etag"] != etag


def test_the_tag_can_be_read_by_a_page_as_well_as_by_the_extension(
    client: TestClient, test_user: User
) -> None:
    key = issue_key(client)

    response = client.get(
        "/api/v1/agent/policy", headers={**bearer(key), "Origin": "http://localhost:5173"}
    )

    assert "etag" in response.headers["access-control-expose-headers"].lower()


def test_changing_a_tool_or_a_setting_also_changes_the_tag(
    client: TestClient, test_user: User, caigo_admin: User, login_as, catalogue
) -> None:
    key = issue_key(client)
    seen = [client.get("/api/v1/agent/policy", headers=bearer(key)).headers["etag"]]

    client.put("/api/v1/ai-use/settings", json={"unapproved_site_action": "warn"})
    seen.append(client.get("/api/v1/agent/policy", headers=bearer(key)).headers["etag"])
    login_as(caigo_admin)
    tool = client.get("/api/v1/ai-tools").json()[0]
    client.post(
        f"/api/v1/ai-tools/{tool['id']}/decision",
        json={"action": "approve", "max_data_classification": "public"},
    )
    seen.append(client.get("/api/v1/agent/policy", headers=bearer(key)).headers["etag"])

    assert len(set(seen)) == 3


# ---------- the counts the extension sends ----------


def test_counts_are_recorded_against_the_catalogued_domain(
    client: TestClient, test_user: User, catalogue
) -> None:
    key = issue_key(client)

    response = send(
        client, key, [event(domain="https://www.ChatGPT.com/c/abc"), event(domain="claude.ai")]
    )

    assert response.status_code == 202, response.text
    assert response.json() == {"accepted": 2}
    by_domain = {d["domain"]: d for d in client.get("/api/v1/ai-use/usage").json()["by_domain"]}
    # A subdomain or a full address is recorded as the catalogue's own domain.
    assert set(by_domain) == {"chatgpt.com", "claude.ai"}
    assert by_domain["chatgpt.com"]["tool_name"] == "ChatGPT"


def test_a_tool_with_nested_domains_is_recorded_at_the_most_specific_one(
    client: TestClient, test_user: User
) -> None:
    client.post(
        "/api/v1/ai-tools",
        json={"name": "Example AI", "domains": ["example.ai", "chat.example.ai"]},
    )
    key = issue_key(client)

    send(
        client, key, [event(domain="https://www.chat.example.ai/x"), event(domain="app.example.ai")]
    )

    domains = {d["domain"] for d in client.get("/api/v1/ai-use/usage").json()["by_domain"]}
    assert domains == {"chat.example.ai", "example.ai"}


def test_the_same_count_sent_again_adds_to_the_row_rather_than_duplicating_it(
    client: TestClient, test_user: User, catalogue, db_session
) -> None:
    from app.models.ai_dlp import AIUsageEvent

    key = issue_key(client)

    send(client, key, [event(count=2)])
    send(client, key, [event(count=3), event(count=4)])
    send(client, key, [event(count=1)], email="someone.else@example.com")

    rows = db_session.query(AIUsageEvent).order_by(AIUsageEvent.user_ref).all()
    assert [(r.user_ref, r.count) for r in rows] == [
        ("elena@example.com", 9),
        ("someone.else@example.com", 1),
    ]


def test_only_catalogued_ai_sites_are_ever_recorded(
    client: TestClient, test_user: User, catalogue, db_session
) -> None:
    from app.models.ai_dlp import AIUsageEvent

    key = issue_key(client)

    for domain in ("example.com", "mail.google.com", "chatgpt.com.evil.net", "notchatgpt.com"):
        response = send(client, key, [event(domain=domain)])
        assert response.status_code == 400, domain
        assert "isn't a catalogued AI site" in response.json()["detail"]
    assert db_session.query(AIUsageEvent).count() == 0


def test_nothing_but_counts_can_be_sent(client: TestClient, test_user: User, catalogue) -> None:
    key = issue_key(client)

    for extra in ({"url": "https://chatgpt.com/c/123"}, {"title": "My tax return"}, {"text": "x"}):
        assert send(client, key, [{**event(), **extra}]).status_code == 422, extra
    body = {"user_email": "a@example.com", "events": [event()], "page_text": "secret"}
    assert client.post("/api/v1/agent/events", headers=bearer(key), json=body).status_code == 422


def test_a_batch_is_taken_whole_or_not_at_all(
    client: TestClient, test_user: User, catalogue, db_session
) -> None:
    from app.models.ai_dlp import AIUsageEvent

    key = issue_key(client)

    response = send(client, key, [event(), event(domain="example.com")])

    assert response.status_code == 400
    assert db_session.query(AIUsageEvent).count() == 0


@pytest.mark.parametrize(
    "bad",
    [
        {"count": 0},
        {"count": 10_001},
        {"event_type": "browsing"},
        {"action": "ignored"},
        {"domain": "x"},
    ],
)
def test_malformed_events_are_refused(
    client: TestClient, test_user: User, catalogue, bad: dict
) -> None:
    key = issue_key(client)

    assert send(client, key, [event(**bad)]).status_code == 422


def test_a_dlp_match_must_name_a_real_rule_and_nothing_else_may(
    client: TestClient, test_user: User, catalogue
) -> None:
    key = issue_key(client)
    rule = make_rule(client)
    match = {"event_type": "dlp_match", "action": "blocked"}

    assert send(client, key, [event(**match)]).status_code == 400  # no rule
    assert send(client, key, [event(**match, rule_id=999)]).status_code == 404
    assert send(client, key, [event(rule_id=rule["id"])]).status_code == 400  # not a match
    assert send(client, key, [event(**match, rule_id=rule["id"], count=2)]).status_code == 202


def test_counts_for_days_outside_what_is_kept_or_in_the_future_are_refused(
    client: TestClient, test_user: User, catalogue
) -> None:
    key = issue_key(client)
    client.put("/api/v1/ai-use/settings", json={"retention_days": 30})

    assert send(client, key, [event(day=days(-31))]).status_code == 400
    assert send(client, key, [event(day=days(2))]).status_code == 400
    assert send(client, key, [event(day=days(-30))]).status_code == 202
    assert send(client, key, [event(day=days(1))]).status_code == 202


def test_the_email_must_look_like_one(client: TestClient, test_user: User, catalogue) -> None:
    key = issue_key(client)

    for bad in ("elena", "elena@", "@example.com", "a b@example.com"):
        assert send(client, key, [event()], email=bad).status_code in (400, 422), bad
    assert send(client, key, [event()], email="  Elena@Example.COM ").status_code == 202
    # Kept lower-case, so one person's counts don't split by how their address was typed.
    users = client.get("/api/v1/ai-use/usage").json()["by_user"]
    assert [u["user_ref"] for u in users] == ["elena@example.com"]


def test_old_counts_are_deleted_when_the_retention_period_shrinks(
    client: TestClient, test_user: User, catalogue, db_session
) -> None:
    from app.models.ai_dlp import AIUsageEvent

    key = issue_key(client)
    send(client, key, [event(day=days(-80)), event(day=days(-10)), event()])
    assert db_session.query(AIUsageEvent).count() == 3

    client.put("/api/v1/ai-use/settings", json={"retention_days": 30})

    assert sorted(e.day.isoformat() for e in db_session.query(AIUsageEvent)) == [days(-10), days(0)]


def test_sending_counts_also_clears_the_ones_that_have_expired(
    client: TestClient, test_user: User, catalogue, db_session
) -> None:
    from app.models.ai_dlp import AIUsageEvent

    key = issue_key(client)
    send(client, key, [event(day=days(-60))])
    client.put("/api/v1/ai-use/settings", json={"retention_days": 90})
    db_session.query(AIUsageEvent).update({AIUsageEvent.day: TODAY - timedelta(days=200)})
    db_session.commit()

    send(client, key, [event()])

    assert [e.day.isoformat() for e in db_session.query(AIUsageEvent)] == [days(0)]


# ---------- the usage dashboard ----------


def test_the_usage_summary_groups_counts_by_site_rule_person_and_day(
    client: TestClient, test_user: User, make_user, catalogue
) -> None:
    key = issue_key(client)
    card = make_rule(client)
    make_user(name="Elena Employee", email="elena@example.com", role=UserRole.EMPLOYEE)
    send(
        client,
        key,
        [
            event(count=3),
            event(event_type="blocked_site", action="blocked", count=2),
            event(day=days(-1), domain="claude.ai", count=4),
            event(
                event_type="dlp_match",
                action="blocked",
                rule_id=card["id"],
                count=5,
            ),
            event(event_type="dlp_match", action="warned", rule_id=card["id"], count=1),
        ],
    )
    send(client, key, [event(count=7)], email="bob@example.com")

    summary = client.get("/api/v1/ai-use/usage").json()

    assert {t["event_type"]: t["count"] for t in summary["by_type"]} == {
        "unapproved_site": 14,
        "blocked_site": 2,
        "dlp_match": 6,
    }
    domains = {d["domain"]: d for d in summary["by_domain"]}
    assert (domains["chatgpt.com"]["unapproved"], domains["chatgpt.com"]["blocked"]) == (12, 2)
    assert domains["chatgpt.com"]["dlp_matches"] == 6
    assert summary["by_rule"] == [
        {"rule_id": card["id"], "rule_name": "Payment card numbers", "matches": 6, "blocked": 5}
    ]
    users = {u["user_ref"]: u for u in summary["by_user"]}
    assert users["elena@example.com"]["user_name"] == "Elena Employee"
    assert (
        users["elena@example.com"]["unapproved"],
        users["elena@example.com"]["dlp_matches"],
    ) == (
        9,
        6,
    )
    assert users["bob@example.com"]["user_name"] is None
    assert [d["day"] for d in summary["by_day"]] == [days(-1), days(0)]
    # Most active first.
    assert summary["by_user"][0]["user_ref"] == "elena@example.com"


def test_the_summary_only_covers_the_period_asked_for(
    client: TestClient, test_user: User, catalogue
) -> None:
    key = issue_key(client)
    send(client, key, [event(day=days(-20), count=5), event(count=1)])

    week = client.get("/api/v1/ai-use/usage", params={"days": 7}).json()
    month = client.get("/api/v1/ai-use/usage", params={"days": 30}).json()

    assert week["by_type"] == [{"event_type": "unapproved_site", "count": 1}]
    assert month["by_type"] == [{"event_type": "unapproved_site", "count": 6}]
    assert client.get("/api/v1/ai-use/usage", params={"days": 0}).status_code == 422


def test_an_empty_summary_is_empty_not_an_error(client: TestClient, test_user: User) -> None:
    summary = client.get("/api/v1/ai-use/usage").json()

    assert summary["by_type"] == summary["by_domain"] == summary["by_user"] == []


# ---------- staff, dashboard, compliance ----------


def test_staff_are_told_what_is_monitored(
    client: TestClient, test_user: User, login_as, make_user
) -> None:
    client.put(
        "/api/v1/ai-use/settings",
        json={"unapproved_site_action": "warn", "staff_notice": "We count visits to AI sites."},
    )
    login_as(make_user(role=UserRole.EMPLOYEE))

    notice = client.get("/api/v1/staff/ai-use-notice").json()

    assert notice == {
        "staff_notice": "We count visits to AI sites.",
        "unapproved_site_action": "warn",
    }


def test_staff_see_a_default_notice_before_anything_is_saved(
    client: TestClient, login_as, make_user
) -> None:
    login_as(make_user(role=UserRole.EMPLOYEE))

    assert client.get("/api/v1/staff/ai-use-notice").json() == {
        "staff_notice": None,
        "unapproved_site_action": "block",
    }


def test_the_dashboard_counts_the_last_seven_days_only(
    client: TestClient, test_user: User, catalogue
) -> None:
    key = issue_key(client)
    rule = make_rule(client)
    send(
        client,
        key,
        [
            event(count=2),
            event(day=days(-6), event_type="blocked_site", action="blocked", count=3),
            event(day=days(-7), count=50),
            event(event_type="dlp_match", action="blocked", rule_id=rule["id"], count=4),
            event(
                day=days(-9), event_type="dlp_match", action="blocked", rule_id=rule["id"], count=90
            ),
        ],
    )

    attention = {a["key"]: a for a in client.get("/api/v1/dashboard/summary").json()["attention"]}

    assert attention["unapproved_ai_use_week"]["count"] == 5
    assert attention["dlp_matches_week"]["count"] == 4
    assert attention["unapproved_ai_use_week"]["group"] == "AI systems, data & suppliers"


def test_ai_use_controls_count_once_staff_are_told_and_a_rule_is_on(
    client: TestClient, test_user: User
) -> None:
    controls = client.get("/api/v1/framework-controls", params={"framework": "iso_42001"}).json()
    control = next(c for c in controls if c["code"] == "A.9.2")
    settings = client.get("/api/v1/ai-use/settings").json()
    client.put(
        "/api/v1/framework-tags",
        params={"entity_type": "AIUseSettings", "entity_id": settings["id"]},
        json={"control_ids": [control["id"]]},
    )

    def detail() -> tuple[bool, str]:
        status = next(
            row
            for row in client.get(
                "/api/v1/compliance-status", params={"framework": "iso_42001"}
            ).json()
            if row["code"] == "A.9.2"
        )
        item = status["tagged_items"][0]
        return item["current"], item["detail"]

    assert detail() == (False, "Staff haven't been told what is monitored")
    client.put("/api/v1/ai-use/settings", json={"staff_notice": "We count visits."})
    assert detail() == (False, "No data-loss-prevention rule is switched on")
    rule = make_rule(client, enabled=False)
    assert detail() == (False, "No data-loss-prevention rule is switched on")
    client.put(f"/api/v1/dlp-rules/{rule['id']}", json={"enabled": True})
    assert detail() == (True, "1 rule(s) on; staff notice published")
    client.put("/api/v1/ai-use/settings", json={"staff_notice": "   "})
    assert detail() == (False, "Staff haven't been told what is monitored")


def test_a_deleted_rule_no_longer_counts_towards_the_controls(
    client: TestClient, test_user: User, db_session
) -> None:
    client.put("/api/v1/ai-use/settings", json={"staff_notice": "We count visits."})
    rule = make_rule(client)

    assert client.delete(f"/api/v1/dlp-rules/{rule['id']}").status_code == 204
    policy_key = issue_key(client)

    assert client.get("/api/v1/agent/policy", headers=bearer(policy_key)).json()["rules"] == []


# ---------- the whole agent surface ----------


def test_every_route_under_agent_refuses_a_caller_without_the_key(
    client: TestClient, make_user: Callable[..., User], login_as
) -> None:
    """Walks the API, so an agent route added later without the key dependency
    fails here. An employee session makes no difference."""
    from app.main import app

    login_as(make_user(role=UserRole.EMPLOYEE))
    checked = 0
    for route_path, operations in app.openapi()["paths"].items():
        if not route_path.startswith("/api/v1/agent/"):
            continue
        for method in operations:
            response = client.request(
                method.upper(), route_path, json={} if method in ("post", "put") else None
            )
            checked += 1
            assert response.status_code == 401, (method, route_path)
    assert checked == 2
