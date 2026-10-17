from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.models.user import User, UserRole

# The server judges "today" in UTC; so do these, so they don't depend on the
# machine's own time zone.
TODAY = datetime.now(UTC).date()


def days(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


def create_tool(client: TestClient, **overrides) -> dict:
    payload = {"name": "Claude", "vendor": "Anthropic", "domains": ["claude.ai"]}
    payload.update(overrides)
    response = client.post("/api/v1/ai-tools", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def decide(client: TestClient, tool_id: int, action: str = "approve", **overrides):
    payload = {"action": action, "max_data_classification": "internal"}
    payload.update(overrides)
    return client.post(f"/api/v1/ai-tools/{tool_id}/decision", json=payload)


@pytest.fixture()
def employee(make_user: Callable[..., User]) -> User:
    return make_user(role=UserRole.EMPLOYEE, name="Elena Employee", email="elena@example.com")


def ask(client: TestClient, **overrides):
    payload = {
        "tool_name": "Perplexity",
        "domain": "perplexity.ai",
        "purpose": "Checking public sources quickly while researching suppliers.",
    }
    payload.update(overrides)
    return client.post("/api/v1/staff/ai-tool-requests", json=payload)


# ---------- the register ----------


def test_a_new_tool_starts_catalogued_with_its_domains_normalised(
    client: TestClient, test_user: User
) -> None:
    body = create_tool(
        client,
        domains=["https://Claude.ai/chat", "claude.ai", "www.claude.ai"],
        owner_id=test_user.id,
    )

    assert body["status"] == "catalogued"
    assert body["domains"] == ["claude.ai", "www.claude.ai"]
    assert body["max_data_classification"] == "public"
    assert body["standing"] == {"review_overdue": False}
    assert [t["id"] for t in client.get("/api/v1/ai-tools").json()] == [body["id"]]


def test_a_tool_needs_a_real_domain_and_one_nobody_else_has(
    client: TestClient, test_user: User
) -> None:
    create_tool(client)

    assert (
        client.post("/api/v1/ai-tools", json={"name": "No domain", "domains": []}).status_code
        == 422
    )
    bad = client.post("/api/v1/ai-tools", json={"name": "Bad", "domains": ["not a domain"]})
    assert bad.status_code == 400
    clash = client.post("/api/v1/ai-tools", json={"name": "Copy", "domains": ["Claude.ai"]})
    assert clash.status_code == 409
    assert "Claude" in clash.json()["detail"]


def test_updating_a_tool_keeps_its_own_domain_but_not_anothers(
    client: TestClient, test_user: User
) -> None:
    tool = create_tool(client)
    other = create_tool(client, name="Perplexity", domains=["perplexity.ai"])
    url = f"/api/v1/ai-tools/{tool['id']}"

    assert client.put(url, json={"domains": ["claude.ai", "console.claude.ai"]}).status_code == 200
    assert client.put(url, json={"domains": ["perplexity.ai"]}).status_code == 409
    assert client.put(url, json={"name": None}).status_code == 400
    assert client.put(url, json={"supplier_id": 999}).status_code == 404
    assert client.get(f"/api/v1/ai-tools/{other['id']}").json()["domains"] == ["perplexity.ai"]


def test_the_built_in_catalogue_is_added_once_and_skips_what_is_there(
    client: TestClient, db_session, test_user: User
) -> None:
    from app.services import ai_tool_service

    create_tool(client, name="Our own Claude entry", domains=["claude.ai"])

    added = ai_tool_service.install_default_catalog(db_session)
    again = ai_tool_service.install_default_catalog(db_session)

    names = [t["name"] for t in client.get("/api/v1/ai-tools").json()]
    assert again == 0
    assert added == len(names) - 1
    assert names.count("Our own Claude entry") == 1
    assert "Claude" not in names
    assert "ChatGPT" in names


def test_only_a_tool_nobody_has_decided_on_or_asked_for_can_be_deleted(
    client: TestClient, test_user: User, caigo_admin: User, login_as, employee: User
) -> None:
    untouched = create_tool(client, name="Untouched", domains=["untouched.example"])
    approved = create_tool(client, name="Approved", domains=["approved.example"])
    requested = create_tool(client, name="Requested", domains=["requested.example"])
    login_as(caigo_admin)
    decide(client, approved["id"])
    login_as(employee)
    assert (
        ask(client, tool_id=requested["id"], tool_name="Requested", domain=None).status_code == 201
    )
    login_as(test_user)

    assert client.delete(f"/api/v1/ai-tools/{approved['id']}").status_code == 409
    assert client.delete(f"/api/v1/ai-tools/{requested['id']}").status_code == 409
    assert client.delete(f"/api/v1/ai-tools/{untouched['id']}").status_code == 204
    assert client.get(f"/api/v1/ai-tools/{untouched['id']}").status_code == 404


# ---------- deciding on a tool ----------


def test_only_the_caigo_can_approve_a_tool(
    client: TestClient, test_user: User, caigo_admin: User, login_as, make_user
) -> None:
    tool = create_tool(client)

    # An administrator who isn't the Chief AI Governance Officer.
    assert decide(client, tool["id"]).status_code == 403
    login_as(make_user(role=UserRole.CONTRIBUTOR))
    assert decide(client, tool["id"]).status_code == 403
    login_as(caigo_admin)
    response = decide(
        client,
        tool["id"],
        max_data_classification="confidential",
        conditions_of_use="Company accounts only.",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "approved"
    assert (body["decided_by"], body["decided_on"]) == (caigo_admin.id, days(0))
    assert body["max_data_classification"] == "confidential"
    assert body["conditions_of_use"] == "Company accounts only."


def test_approving_sets_a_review_a_year_on_unless_one_is_given(
    client: TestClient, test_user: User, caigo_admin: User, login_as
) -> None:
    first = create_tool(client)
    second = create_tool(client, name="Perplexity", domains=["perplexity.ai"])
    login_as(caigo_admin)

    default = decide(client, first["id"]).json()
    chosen = decide(client, second["id"], review_due=days(90)).json()

    assert default["review_due"] == str(TODAY.replace(year=TODAY.year + 1)) or default[
        "review_due"
    ] == str(TODAY.replace(year=TODAY.year + 1, day=28))
    assert chosen["review_due"] == days(90)


def test_approving_needs_to_say_what_data_the_tool_may_be_given(
    client: TestClient, test_user: User, caigo_admin: User, login_as
) -> None:
    tool = create_tool(client)
    login_as(caigo_admin)

    response = client.post(f"/api/v1/ai-tools/{tool['id']}/decision", json={"action": "approve"})

    assert response.status_code == 400


def test_a_tool_can_be_restricted_then_approved_then_revoked_with_a_reason(
    client: TestClient, test_user: User, caigo_admin: User, login_as
) -> None:
    tool = create_tool(client)
    login_as(caigo_admin)

    assert decide(client, tool["id"], "restrict").json()["status"] == "restricted"
    assert decide(client, tool["id"], "restrict").status_code == 409  # already
    assert decide(client, tool["id"], "approve").json()["status"] == "approved"
    assert decide(client, tool["id"], "revoke").status_code == 400  # needs a reason
    revoked = decide(client, tool["id"], "revoke", note="Vendor breach notified").json()

    assert revoked["status"] == "revoked"
    assert (revoked["review_due"], revoked["decision_note"]) == (
        None,
        "Vendor breach notified",
    )


def test_a_tool_never_approved_cant_be_revoked(
    client: TestClient, test_user: User, caigo_admin: User, login_as
) -> None:
    tool = create_tool(client)
    login_as(caigo_admin)

    assert decide(client, tool["id"], "revoke", note="Why not").status_code == 409


def test_a_tool_can_be_tied_to_its_supplier_record(client: TestClient, test_user: User) -> None:
    supplier = client.post(
        "/api/v1/suppliers", json={"name": "Anthropic", "supplier_type": "model_provider"}
    )
    assert supplier.status_code == 201, supplier.text

    tool = create_tool(client, supplier_id=supplier.json()["id"])

    assert tool["supplier_id"] == supplier.json()["id"]


# ---------- what staff see ----------


def test_staff_see_approved_and_restricted_tools_with_their_rules_and_nothing_else(
    client: TestClient, test_user: User, caigo_admin: User, login_as, employee: User
) -> None:
    approved = create_tool(client, name="Claude", domains=["claude.ai"])
    restricted = create_tool(client, name="Perplexity", domains=["perplexity.ai"])
    create_tool(client, name="Unapproved", domains=["unapproved.example"])
    revoked = create_tool(client, name="Gone", domains=["gone.example"])
    login_as(caigo_admin)
    decide(client, approved["id"], conditions_of_use="Company accounts only.")
    decide(client, restricted["id"], "restrict", max_data_classification="public")
    decide(client, revoked["id"])
    decide(client, revoked["id"], "revoke", note="Withdrawn")
    login_as(employee)

    listed = client.get("/api/v1/staff/ai-tools").json()

    assert {t["name"] for t in listed} == {"Claude", "Perplexity"}
    claude = next(t for t in listed if t["name"] == "Claude")
    assert claude == {
        "id": approved["id"],
        "name": "Claude",
        "vendor": "Anthropic",
        "domains": ["claude.ai"],
        "status": "approved",
        "max_data_classification": "internal",
        "conditions_of_use": "Company accounts only.",
    }


def test_staff_can_pick_a_known_tool_that_isnt_allowed_yet(
    client: TestClient, test_user: User, caigo_admin: User, login_as, employee: User
) -> None:
    create_tool(client, name="Claude", domains=["claude.ai"])
    allowed = create_tool(client, name="Perplexity", domains=["perplexity.ai"])
    login_as(caigo_admin)
    decide(client, allowed["id"])
    login_as(employee)

    requestable = client.get("/api/v1/staff/ai-tools/requestable").json()

    assert [t["name"] for t in requestable] == ["Claude"]
    assert set(requestable[0]) == {"id", "name", "vendor"}


# ---------- requests ----------


def test_an_employee_asks_for_a_tool_and_sees_it_waiting(
    client: TestClient, login_as, employee: User
) -> None:
    login_as(employee)

    response = ask(client, data_involved="Public web pages only")

    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["status"], body["domain"], body["requested_on"]) == (
        "requested",
        "perplexity.ai",
        days(0),
    )
    # Only what the employee needs: no requester id, no decision internals.
    assert set(body) == {
        "id",
        "tool_name",
        "domain",
        "purpose",
        "requested_on",
        "status",
        "decided_on",
        "decision_note",
    }
    assert [r["id"] for r in client.get("/api/v1/staff/ai-tool-requests/mine").json()] == [
        body["id"]
    ]


def test_a_request_needs_a_reason_and_a_valid_address(
    client: TestClient, login_as, employee
) -> None:
    login_as(employee)

    assert ask(client, purpose="short").status_code == 422
    assert ask(client, domain="not a domain").status_code == 400
    assert ask(client, domain=None).status_code == 201  # the address is optional


def test_asking_twice_for_the_same_tool_is_refused_while_the_first_waits(
    client: TestClient, login_as, employee: User
) -> None:
    login_as(employee)
    ask(client)

    assert ask(client).status_code == 409
    assert ask(client, tool_name="PERPLEXITY").status_code == 409
    assert ask(client, tool_name="Something else", domain="else.example").status_code == 201


def test_asking_for_a_tool_that_is_already_allowed_points_to_the_list(
    client: TestClient, test_user: User, caigo_admin: User, login_as, employee: User
) -> None:
    tool = create_tool(client, name="Perplexity", domains=["perplexity.ai"])
    login_as(caigo_admin)
    decide(client, tool["id"])
    login_as(employee)

    by_id = ask(client, tool_id=tool["id"])
    by_address = ask(client, tool_name="Same thing", domain="www.perplexity.ai")

    assert by_id.status_code == 400
    assert by_address.status_code == 400
    assert "already approved" in by_address.json()["detail"]


def test_each_employee_sees_only_their_own_requests(
    client: TestClient, login_as, employee: User, make_user
) -> None:
    other = make_user(role=UserRole.EMPLOYEE)
    login_as(employee)
    ask(client)
    login_as(other)

    assert client.get("/api/v1/staff/ai-tool-requests/mine").json() == []


def test_approving_a_request_for_a_new_tool_catalogues_and_approves_it(
    client: TestClient, test_user: User, caigo_admin: User, login_as, employee: User
) -> None:
    login_as(employee)
    request = ask(client).json()
    login_as(caigo_admin)

    response = client.post(
        f"/api/v1/ai-tools/requests/{request['id']}/decision",
        json={
            "action": "approve",
            "max_data_classification": "public",
            "conditions_of_use": "No customer data.",
            "note": "Fine for research",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["status"], body["decided_by"], body["decided_on"]) == (
        "approved",
        caigo_admin.id,
        days(0),
    )
    tool = client.get(f"/api/v1/ai-tools/{body['tool_id']}").json()
    assert (tool["name"], tool["domains"], tool["status"]) == (
        "Perplexity",
        ["perplexity.ai"],
        "approved",
    )
    assert tool["conditions_of_use"] == "No customer data."
    login_as(employee)
    assert [t["name"] for t in client.get("/api/v1/staff/ai-tools").json()] == ["Perplexity"]
    mine = client.get("/api/v1/staff/ai-tool-requests/mine").json()[0]
    assert (mine["status"], mine["decision_note"]) == ("approved", "Fine for research")


def test_approving_a_request_for_a_catalogued_tool_approves_that_tool(
    client: TestClient, test_user: User, caigo_admin: User, login_as, employee: User
) -> None:
    tool = create_tool(client, name="Claude", domains=["claude.ai"])
    login_as(employee)
    request = ask(client, tool_id=tool["id"], tool_name="Claude", domain=None).json()
    login_as(caigo_admin)

    client.post(
        f"/api/v1/ai-tools/requests/{request['id']}/decision",
        json={"action": "approve", "max_data_classification": "internal"},
    )

    assert client.get(f"/api/v1/ai-tools/{tool['id']}").json()["status"] == "approved"
    assert len(client.get("/api/v1/ai-tools").json()) == 1


def test_a_request_with_no_address_cant_be_approved_until_one_is_given(
    client: TestClient, test_user: User, caigo_admin: User, login_as, employee: User
) -> None:
    login_as(employee)
    request = ask(client, tool_name="Mystery AI", domain=None).json()
    login_as(caigo_admin)
    url = f"/api/v1/ai-tools/requests/{request['id']}/decision"
    body = {"action": "approve", "max_data_classification": "public"}

    assert client.post(url, json=body).status_code == 400
    assert client.post(url, json={**body, "domain": "mystery.ai"}).status_code == 200
    assert client.get("/api/v1/ai-tools").json()[0]["domains"] == ["mystery.ai"]


def test_rejecting_a_request_needs_a_reason_the_employee_can_read(
    client: TestClient, test_user: User, caigo_admin: User, login_as, employee: User
) -> None:
    login_as(employee)
    request = ask(client).json()
    login_as(caigo_admin)
    url = f"/api/v1/ai-tools/requests/{request['id']}/decision"

    assert client.post(url, json={"action": "reject"}).status_code == 400
    assert client.post(url, json={"action": "reject", "note": "   "}).status_code == 400
    rejected = client.post(url, json={"action": "reject", "note": "Data leaves the EU"})

    assert rejected.json()["status"] == "rejected"
    login_as(employee)
    mine = client.get("/api/v1/staff/ai-tool-requests/mine").json()[0]
    assert (mine["status"], mine["decision_note"]) == ("rejected", "Data leaves the EU")
    assert client.get("/api/v1/staff/ai-tools").json() == []
    # A rejected request doesn't block asking again.
    assert ask(client).status_code == 201


def test_a_request_is_decided_once_and_only_by_the_caigo(
    client: TestClient, test_user: User, caigo_admin: User, login_as, employee: User
) -> None:
    login_as(employee)
    request = ask(client).json()
    url = f"/api/v1/ai-tools/requests/{request['id']}/decision"
    approve = {"action": "approve", "max_data_classification": "public"}

    assert client.post(url, json=approve).status_code == 403  # an employee
    login_as(test_user)
    assert client.post(url, json=approve).status_code == 403  # an admin, not the CAIGO
    login_as(caigo_admin)
    assert client.post(url, json=approve).status_code == 200
    assert client.post(url, json=approve).status_code == 409


def test_rejecting_is_the_caigos_call_too(
    client: TestClient, test_user: User, caigo_admin: User, login_as, employee: User
) -> None:
    login_as(employee)
    request = ask(client).json()
    login_as(test_user)  # an administrator who isn't the Chief AI Governance Officer
    url = f"/api/v1/ai-tools/requests/{request['id']}/decision"

    refused = client.post(url, json={"action": "reject", "note": "No"})

    assert refused.status_code == 403
    assert client.get(f"/api/v1/ai-tools/requests/{request['id']}").json()["status"] == "requested"


def test_a_review_date_set_on_a_tool_nobody_has_approved_isnt_overdue(
    client: TestClient, test_user: User
) -> None:
    tool = create_tool(client)

    client.put(f"/api/v1/ai-tools/{tool['id']}", json={"review_due": days(-30)})

    assert client.get(f"/api/v1/ai-tools/{tool['id']}").json()["standing"] == {
        "review_overdue": False
    }
    attention = {a["key"] for a in client.get("/api/v1/dashboard/summary").json()["attention"]}
    assert "ai_tools_review_overdue" not in attention


def test_nobody_decides_their_own_request(
    client: TestClient, db_session, caigo_admin: User, login_as
) -> None:
    from app.schemas.ai_tool import AIToolRequestCreate
    from app.services import ai_tool_service

    request = ai_tool_service.create_request(
        db_session,
        AIToolRequestCreate(
            tool_name="Own request",
            domain="own.example",
            purpose="The Chief AI Governance Officer asks for a tool.",
        ),
        requester_id=caigo_admin.id,
    )
    login_as(caigo_admin)

    response = client.post(
        f"/api/v1/ai-tools/requests/{request.id}/decision",
        json={"action": "approve", "max_data_classification": "public"},
    )

    assert response.status_code == 409
    assert "own request" in response.json()["detail"]


def test_the_request_queue_lists_every_request_for_the_governance_team(
    client: TestClient, test_user: User, login_as, employee: User
) -> None:
    login_as(employee)
    ask(client)
    login_as(test_user)

    queue = client.get("/api/v1/ai-tools/requests").json()

    assert [(r["tool_name"], r["requester_id"], r["status"]) for r in queue] == [
        ("Perplexity", employee.id, "requested")
    ]
    assert client.get(f"/api/v1/ai-tools/requests/{queue[0]['id']}").status_code == 200
    assert client.get("/api/v1/ai-tools/requests/999").status_code == 404


# ---------- dashboard and compliance ----------


def test_the_dashboard_counts_waiting_requests_and_overdue_reviews(
    client: TestClient, test_user: User, caigo_admin: User, login_as, employee: User
) -> None:
    tool = create_tool(client)
    login_as(caigo_admin)
    decide(client, tool["id"], review_due=days(-3))
    login_as(employee)
    ask(client)
    login_as(test_user)

    attention = {a["key"]: a for a in client.get("/api/v1/dashboard/summary").json()["attention"]}

    assert attention["ai_tool_requests_pending"]["count"] == 1
    assert attention["ai_tools_review_overdue"]["count"] == 1
    assert attention["ai_tool_requests_pending"]["group"] == "AI systems, data & suppliers"


def test_a_tool_tagged_to_a_control_counts_only_once_decided_and_in_date(
    client: TestClient, test_user: User, caigo_admin: User, login_as
) -> None:
    controls = client.get("/api/v1/framework-controls", params={"framework": "iso_42001"}).json()
    control = next(c for c in controls if c["code"] == "A.9.2")
    catalogued = create_tool(client, name="Catalogued", domains=["catalogued.example"])
    current = create_tool(client, name="Current", domains=["current.example"])
    stale = create_tool(client, name="Stale", domains=["stale.example"])
    gone = create_tool(client, name="Gone", domains=["gone.example"])
    login_as(caigo_admin)
    decide(client, current["id"], review_due=days(30))
    decide(client, stale["id"], review_due=days(-1))
    decide(client, gone["id"])
    decide(client, gone["id"], "revoke", note="Withdrawn")
    login_as(test_user)
    for tool in (catalogued, current, stale, gone):
        client.put(
            "/api/v1/framework-tags",
            params={"entity_type": "AITool", "entity_id": tool["id"]},
            json={"control_ids": [control["id"]]},
        )

    status = next(
        row
        for row in client.get("/api/v1/compliance-status", params={"framework": "iso_42001"}).json()
        if row["code"] == "A.9.2"
    )

    details = {item["label"]: (item["current"], item["detail"]) for item in status["tagged_items"]}
    assert details == {
        "Catalogued": (False, "Known, but no decision has been made on it"),
        "Current": (True, f"Approved, review due {days(30)}"),
        "Stale": (False, f"Review overdue since {days(-1)}"),
        "Gone": (True, "Access withdrawn"),
    }
    assert status["status"] == "partial"


# ---------- access ----------


def test_viewers_can_read_the_register_but_not_change_it(
    client: TestClient, test_user: User, login_as, make_user
) -> None:
    tool = create_tool(client)
    login_as(make_user(role=UserRole.VIEWER))

    assert client.get(f"/api/v1/ai-tools/{tool['id']}").status_code == 200
    assert (
        client.post("/api/v1/ai-tools", json={"name": "X", "domains": ["x.example"]}).status_code
        == 403
    )
    assert decide(client, tool["id"]).status_code == 403


def test_an_employee_cant_reach_the_register_or_its_queue(
    client: TestClient, login_as, employee: User
) -> None:
    login_as(employee)

    assert client.get("/api/v1/ai-tools").status_code == 403
    assert client.get("/api/v1/ai-tools/requests").status_code == 403
    assert (
        client.post("/api/v1/ai-tools/requests/1/decision", json={"action": "reject"}).status_code
        == 403
    )
