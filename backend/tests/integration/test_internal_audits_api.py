from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.core import audit_schedule
from app.models.user import User


def create_program(client: TestClient, **overrides) -> dict:
    payload = {
        "title": "AI System Inventory Audit Program",
        "schedule_type": "interval",
        "interval_months": 6,
        "start_date": (date.today() - timedelta(days=1)).isoformat(),
    }
    payload.update(overrides)
    response = client.post("/api/v1/audit-programs", json=payload)
    assert response.status_code == 201
    return response.json()


def create_audit(client: TestClient, program_id: int, **overrides) -> dict:
    payload = {"title": "Q1 Audit", "planned_date": date.today().isoformat()}
    payload.update(overrides)
    response = client.post(f"/api/v1/audit-programs/{program_id}/audits", json=payload)
    assert response.status_code == 201
    return response.json()


def test_interval_program_requires_interval_months(client: TestClient, test_user: User) -> None:
    response = client.post(
        "/api/v1/audit-programs",
        json={"title": "No interval given", "schedule_type": "interval"},
    )

    assert response.status_code == 422


def test_ad_hoc_program_has_no_due_date_and_is_never_overdue(
    client: TestClient, test_user: User
) -> None:
    created = create_program(
        client,
        title="One-off vendor audit",
        schedule_type="ad_hoc",
        interval_months=None,
        start_date=(date.today() - timedelta(days=365)).isoformat(),
    )

    assert created["schedule_type"] == "ad_hoc"
    assert created["interval_months"] is None
    assert created["next_due_date"] is None
    assert created["overdue"] is False


def test_interval_program_with_a_past_start_date_and_no_audits_yet_is_overdue(
    client: TestClient, test_user: User
) -> None:
    created = create_program(client)

    assert created["next_due_date"] == (date.today() - timedelta(days=1)).isoformat()
    assert created["overdue"] is True


def test_completing_an_audit_advances_the_programs_next_due_date(
    client: TestClient, test_user: User
) -> None:
    program = create_program(client)
    audit = create_audit(client, program["id"])

    conducted = date.today().isoformat()
    response = client.post(
        f"/api/v1/audit-programs/{program['id']}/audits/{audit['id']}/complete",
        params={"conducted_date": conducted, "conclusion": "No major nonconformities found."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    refreshed = client.get(f"/api/v1/audit-programs/{program['id']}").json()
    expected_next_due = audit_schedule.next_audit_date(date.today(), 6)
    assert refreshed["next_due_date"] == expected_next_due.isoformat()
    assert refreshed["overdue"] is False


def test_archived_program_is_never_overdue(client: TestClient, test_user: User) -> None:
    program = create_program(client)

    archived = client.put(
        f"/api/v1/audit-programs/{program['id']}", json={"status": "archived"}
    ).json()

    assert archived["overdue"] is False
    assert archived["next_due_date"] is None


def test_direct_status_update_cannot_mark_an_audit_completed(
    client: TestClient, test_user: User
) -> None:
    program = create_program(client)
    audit = create_audit(client, program["id"])

    response = client.put(
        f"/api/v1/audit-programs/{program['id']}/audits/{audit['id']}",
        json={"status": "completed"},
    )

    assert response.status_code == 409


def test_a_completed_audit_cannot_be_edited(client: TestClient, test_user: User) -> None:
    program = create_program(client)
    audit = create_audit(client, program["id"])
    client.post(f"/api/v1/audit-programs/{program['id']}/audits/{audit['id']}/complete")

    response = client.put(
        f"/api/v1/audit-programs/{program['id']}/audits/{audit['id']}",
        json={"title": "Renamed"},
    )

    assert response.status_code == 409


def test_deleting_a_program_cascades_its_audits_and_findings(
    client: TestClient, test_user: User
) -> None:
    program = create_program(client)
    audit = create_audit(client, program["id"])
    client.post(
        f"/api/v1/audit-programs/{program['id']}/audits/{audit['id']}/findings",
        json={"description": "Missing evidence for a risk item.", "finding_type": "nonconformity"},
    )

    response = client.delete(f"/api/v1/audit-programs/{program['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/v1/audit-programs/{program['id']}").status_code == 404


def test_raising_a_corrective_action_from_a_finding_is_visible_on_both_sides(
    client: TestClient, test_user: User
) -> None:
    program = create_program(client)
    audit = create_audit(client, program["id"])
    finding = client.post(
        f"/api/v1/audit-programs/{program['id']}/audits/{audit['id']}/findings",
        json={
            "description": "Risk items were closed without evidence attached.",
            "finding_type": "nonconformity",
        },
    ).json()
    assert finding["corrective_action_ids"] == []

    corrective_action = client.post(
        "/api/v1/corrective-actions",
        json={
            "title": "Attach evidence before closing risk items",
            "nonconformity_description": finding["description"],
            "source_type": "AuditFinding",
            "source_id": finding["id"],
            "assignee_id": test_user.id,
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
        },
    ).json()

    refreshed_finding = client.get(
        f"/api/v1/audit-programs/{program['id']}/audits/{audit['id']}/findings"
    ).json()[0]
    assert refreshed_finding["corrective_action_ids"] == [corrective_action["id"]]
    assert corrective_action["source_type"] == "AuditFinding"
    assert corrective_action["source_id"] == finding["id"]
