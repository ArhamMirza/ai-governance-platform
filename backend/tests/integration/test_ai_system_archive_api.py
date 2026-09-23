"""Retirement, sign-off, retention and the archive.

Builds on the gated walk in test_ai_system_lifecycle_api -- these start from
a system already in Operation & Monitoring.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.services import governance_role_service
from tests.integration.test_ai_system_lifecycle_api import (
    LIFECYCLE,
    advance,
    lifecycle,
    make_system,
    reach_deployment,
    requirement,
    upload,
)

_TODAY = datetime.now(UTC).date()
FUTURE = str(_TODAY + timedelta(days=365))
PAST = str(_TODAY - timedelta(days=1))


def reach_operation(client: TestClient, login_as, caigo_admin) -> int:
    row_id = make_system(client)
    reach_deployment(client, row_id, login_as, caigo_admin)
    upload(client, row_id, "monitoring_plan")
    client.put(
        LIFECYCLE.format(row_id=row_id) + "/monitoring",
        json={"monitoring_owner_id": 1, "incident_escalation_path": "Page the ML on-call."},
    )
    advance(client, row_id)
    assert lifecycle(client, row_id)["current_stage"] == "operation_and_monitoring"
    return row_id


def set_retirement(client: TestClient, row_id: int, **data):
    return client.put(LIFECYCLE.format(row_id=row_id) + "/retirement", json=data)


def archive(client: TestClient, row_id: int):
    return client.post(LIFECYCLE.format(row_id=row_id) + "/archive")


# --- Operation & Monitoring -> Retirement ----------------------------------


def test_retiring_needs_a_reason_and_an_approval(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    row_id = reach_operation(client, login_as, caigo_admin)

    body = lifecycle(client, row_id)
    assert requirement(body, "retirement_reason")["satisfied"] is False
    assert requirement(body, "retirement_approved")["satisfied"] is False
    assert advance(client, row_id).status_code == 400

    # reach_operation leaves the session as caigo_admin (the deployment
    # approver) -- switch to a different requester so the retirement
    # approval below isn't blocked as a self-approval.
    login_as(test_user)
    set_retirement(client, row_id, retirement_reason="Replaced by a vendor product.")
    client.post(LIFECYCLE.format(row_id=row_id) + "/request-retirement-approval")
    login_as(caigo_admin)
    client.post(LIFECYCLE.format(row_id=row_id) + "/approve-retirement")

    assert advance(client, row_id).json()["current_stage"] == "retirement"


def test_the_requester_cannot_approve_their_own_retirement(
    client: TestClient, db_session: Session, login_as, caigo_admin, test_user, second_user: User
) -> None:
    # A backup approver exists so the request itself is allowed (see
    # test_cannot_request_retirement_approval_when_you_are_the_only_possible_approver
    # for that guard on its own) -- this test is about the separate rule
    # that the requester still can't approve their own retirement regardless.
    governance_role_service.delegate_caigo(
        db_session, second_user.id, datetime.now(UTC) + timedelta(days=1), actor_id=None
    )
    row_id = reach_operation(client, login_as, caigo_admin)
    # reach_operation leaves the session logged in as caigo_admin (the
    # deployment approver), so the retirement requester here is caigo_admin
    # too -- exactly the self-approval case this test is about.
    client.post(LIFECYCLE.format(row_id=row_id) + "/request-retirement-approval")

    response = client.post(LIFECYCLE.format(row_id=row_id) + "/approve-retirement")

    assert response.status_code == 409
    assert "someone else has to approve it" in response.text


def test_cannot_request_retirement_approval_when_you_are_the_only_possible_approver(
    client: TestClient, login_as, caigo_admin
) -> None:
    row_id = reach_operation(client, login_as, caigo_admin)
    # reach_operation leaves the session logged in as caigo_admin, the sole
    # CAIGO with no backup approver set.

    response = client.post(LIFECYCLE.format(row_id=row_id) + "/request-retirement-approval")

    assert response.status_code == 400
    assert "backup approver" in response.json()["detail"]


def test_approving_a_retirement_requires_the_approve_permission(
    client: TestClient, make_user, login_as, caigo_admin
) -> None:
    row_id = reach_operation(client, login_as, caigo_admin)
    login_as(make_user(role=UserRole.CONTRIBUTOR))

    response = client.post(LIFECYCLE.format(row_id=row_id) + "/approve-retirement")

    assert response.status_code == 403


def test_non_caigo_admin_cannot_approve_a_retirement(
    client: TestClient, make_user, login_as, caigo_admin
) -> None:
    row_id = reach_operation(client, login_as, caigo_admin)
    client.post(LIFECYCLE.format(row_id=row_id) + "/request-retirement-approval")
    login_as(make_user(role=UserRole.ADMIN))

    response = client.post(LIFECYCLE.format(row_id=row_id) + "/approve-retirement")

    assert response.status_code == 403


# --- Retirement -> archived ------------------------------------------------


def reach_retirement(client: TestClient, login_as, caigo_admin, test_user) -> int:
    row_id = reach_operation(client, login_as, caigo_admin)
    # Same reasoning as test_retiring_needs_a_reason_and_an_approval: switch
    # off caigo_admin (still logged in from the deployment approval) so
    # requesting retirement approval isn't a self-approval once caigo_admin
    # approves it below.
    login_as(test_user)
    set_retirement(client, row_id, retirement_reason="Replaced by a vendor product.")
    client.post(LIFECYCLE.format(row_id=row_id) + "/request-retirement-approval")
    login_as(caigo_admin)
    client.post(LIFECYCLE.format(row_id=row_id) + "/approve-retirement")
    advance(client, row_id)
    return row_id


def test_archiving_needs_a_signoff_document_and_a_retention_period(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    row_id = reach_retirement(client, login_as, caigo_admin, test_user)

    body = lifecycle(client, row_id)
    assert body["can_advance"] is False  # Retirement is the last stage.
    assert body["can_archive"] is False
    assert requirement(body, "retirement_signoff")["satisfied"] is False
    assert requirement(body, "retention_until")["satisfied"] is False
    assert archive(client, row_id).status_code == 400

    upload(client, row_id, "retirement_signoff")
    set_retirement(
        client, row_id, retirement_reason="Replaced.", retention_until=FUTURE
    )

    assert lifecycle(client, row_id)["can_archive"] is True
    body = archive(client, row_id).json()
    assert body["is_archived"] is True
    assert body["retired_at"] is not None
    assert body["retention_expired"] is False


def test_only_a_retired_system_can_be_archived(client: TestClient) -> None:
    row_id = make_system(client)

    response = archive(client, row_id)

    assert response.status_code == 409
    assert "Retirement stage" in response.text


def test_archiving_twice_is_rejected(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    row_id = reach_retirement(client, login_as, caigo_admin, test_user)
    upload(client, row_id, "retirement_signoff")
    set_retirement(client, row_id, retirement_reason="Replaced.", retention_until=FUTURE)
    archive(client, row_id)

    assert archive(client, row_id).status_code == 409


# --- The archive itself ----------------------------------------------------


def archive_a_system(client: TestClient, login_as, caigo_admin, test_user, retention: str) -> int:
    row_id = reach_retirement(client, login_as, caigo_admin, test_user)
    upload(client, row_id, "retirement_signoff")
    set_retirement(
        client, row_id, retirement_reason="Replaced by a vendor product.",
        retention_until=retention,
    )
    assert archive(client, row_id).status_code == 200
    return row_id


def test_an_archived_system_leaves_the_active_inventory(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    row_id = archive_a_system(client, login_as, caigo_admin, test_user, FUTURE)

    inventory = client.get("/api/v1/ai-system-inventory").json()
    assert [row["id"] for row in inventory["rows"]] == []

    archived = client.get("/api/v1/ai-systems/archive").json()
    assert [entry["ai_system_row_id"] for entry in archived] == [row_id]
    assert archived[0]["retirement_reason"] == "Replaced by a vendor product."
    assert archived[0]["retention_until"] == FUTURE


def test_an_archived_system_is_not_counted_as_unassessed(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    """A retired system shouldn't drag down governance coverage."""
    archive_a_system(client, login_as, caigo_admin, test_user, FUTURE)

    summary = client.get("/api/v1/dashboard/summary").json()

    assert summary["coverage"]["ai_systems_total"] == 0
    assert summary["ai_systems"]["total"] == 0


def test_the_record_survives_archiving(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    """The point of the archive is that everything stays auditable."""
    row_id = archive_a_system(client, login_as, caigo_admin, test_user, FUTURE)

    assert client.get(LIFECYCLE.format(row_id=row_id)).status_code == 200
    documents = client.get(
        "/api/v1/evidence", params={"entity_type": "AISystem", "entity_id": row_id}
    ).json()
    assert len(documents) > 0
    history = client.get(
        "/api/v1/audit-log", params={"entity_type": "AISystem", "entity_id": row_id}
    ).json()
    assert any(entry["action"] == "archived" for entry in history)


# --- Retention -------------------------------------------------------------


def test_an_archived_system_cannot_be_deleted_before_its_retention_date(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    row_id = archive_a_system(client, login_as, caigo_admin, test_user, FUTURE)

    response = client.delete(f"/api/v1/ai-system-inventory/rows/{row_id}")

    assert response.status_code == 409
    assert FUTURE in response.text
    assert client.get(LIFECYCLE.format(row_id=row_id)).status_code == 200


def test_an_archived_system_can_be_deleted_once_retention_has_passed(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    row_id = archive_a_system(client, login_as, caigo_admin, test_user, PAST)

    listing = client.get("/api/v1/ai-systems/archive").json()
    assert listing[0]["retention_expired"] is True

    assert client.delete(f"/api/v1/ai-system-inventory/rows/{row_id}").status_code == 204
    assert client.get("/api/v1/ai-systems/archive").json() == []


def test_expired_retention_is_surfaced_on_the_dashboard(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    archive_a_system(client, login_as, caigo_admin, test_user, PAST)

    attention = client.get("/api/v1/dashboard/summary").json()["attention"]

    expired = next(item for item in attention if item["key"] == "retention_expired")
    assert expired["count"] == 1


def test_reimporting_the_inventory_does_not_disturb_an_archived_systems_retention(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    """The bug this reproduces: a plain re-upload of the AI System Inventory
    used to delete every row and recreate them, and SQLite reuses a freed
    id -- so re-uploading a file that simply doesn't mention the archived
    system (a filtered export, an "active systems only" roster) could
    silently attach its retention-protected life cycle to whatever new row
    landed on the freed id, while its own row vanished. The archived
    system's row and lifecycle now survive a re-upload that never mentions
    it, exactly as they'd survive any other operation that isn't its own
    delete action."""
    archived_id = archive_a_system(client, login_as, caigo_admin, test_user, FUTURE)
    active_id = make_system(client, name="Fraud Detector")

    # A file mentioning only the still-active system -- the archived one is
    # not in it at all, matched by id or otherwise.
    csv_content = f"ID,Name\n{active_id},Fraud Detector v2\n".encode()
    response = client.post(
        "/api/v1/ai-system-inventory/upload",
        files={"file": ("reimport.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200

    archived_lifecycle = lifecycle(client, archived_id)
    assert archived_lifecycle["is_archived"] is True
    assert archived_lifecycle["retention_until"] == FUTURE
    assert archived_lifecycle["retention_expired"] is False

    listing = client.get("/api/v1/ai-system-inventory").json()
    assert [row["id"] for row in listing["rows"]] == [active_id]
    assert listing["rows"][0]["data"]["name"] == "Fraud Detector v2"

    archive_listing = client.get("/api/v1/ai-systems/archive").json()
    assert [entry["ai_system_row_id"] for entry in archive_listing] == [archived_id]


# --- Once archived, the record does not move -------------------------------
#
# Retention only means something if the record it protects can't be quietly
# rewritten out from under it: extending or shortening retention_until (or
# reverting the stage, or anything else about the record) after archiving
# would undo the one guarantee the archive is supposed to make. The UI
# already disables these controls once a system shows is_archived -- these
# tests are the server-side half of that, since a client can't be trusted to
# be the only thing enforcing it.


def test_retention_cannot_be_rewritten_once_archived(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    row_id = archive_a_system(client, login_as, caigo_admin, test_user, PAST)

    response = set_retirement(
        client, row_id, retirement_reason="Changed my mind", retention_until=FUTURE
    )

    assert response.status_code == 409
    assert "archived" in response.text
    body = lifecycle(client, row_id)
    assert body["retention_until"] == PAST
    assert body["retention_expired"] is True


def test_an_archived_system_cannot_be_reverted_back_to_active(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    row_id = archive_a_system(client, login_as, caigo_admin, test_user, FUTURE)

    response = client.post(
        LIFECYCLE.format(row_id=row_id) + "/revert", json={"reason": "Actually still needed"}
    )

    assert response.status_code == 409
    assert lifecycle(client, row_id)["current_stage"] == "retirement"


def test_an_archived_systems_owner_cannot_be_changed(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    row_id = archive_a_system(client, login_as, caigo_admin, test_user, FUTURE)

    response = client.put(LIFECYCLE.format(row_id=row_id) + "/owner", json={"owner_id": 1})

    assert response.status_code == 409


def test_an_archived_systems_monitoring_cannot_be_changed(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    row_id = archive_a_system(client, login_as, caigo_admin, test_user, FUTURE)

    response = client.put(
        LIFECYCLE.format(row_id=row_id) + "/monitoring",
        json={"monitoring_owner_id": 1, "incident_escalation_path": "New path"},
    )

    assert response.status_code == 409


def test_an_archived_systems_deployment_record_cannot_be_changed(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    row_id = archive_a_system(client, login_as, caigo_admin, test_user, FUTURE)

    response = client.put(
        LIFECYCLE.format(row_id=row_id) + "/deployment-record",
        json={"deployment_environment": "staging", "deployment_version": "9.9",
              "deployed_at": str(_TODAY)},
    )

    assert response.status_code == 409


def test_an_archived_system_cannot_be_resubmitted_for_deployment_approval(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    row_id = archive_a_system(client, login_as, caigo_admin, test_user, FUTURE)

    response = client.post(
        LIFECYCLE.format(row_id=row_id) + "/request-deployment-approval"
    )

    assert response.status_code == 409


def test_an_archived_system_cannot_be_resubmitted_for_retirement_approval(
    client: TestClient, login_as, caigo_admin, test_user
) -> None:
    row_id = archive_a_system(client, login_as, caigo_admin, test_user, FUTURE)

    response = client.post(
        LIFECYCLE.format(row_id=row_id) + "/request-retirement-approval"
    )

    assert response.status_code == 409
