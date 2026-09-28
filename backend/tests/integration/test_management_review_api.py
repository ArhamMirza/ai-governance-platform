from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.user import User


def test_settings_default_to_no_schedule(client: TestClient, test_user: User) -> None:
    response = client.get("/api/v1/management-review/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["interval_months"] is None
    assert body["next_due_date"] is None
    assert body["overdue"] is False


def test_configuring_an_interval_requires_a_start_date(client: TestClient, test_user: User) -> None:
    response = client.put("/api/v1/management-review/settings", json={"interval_months": 12})

    assert response.status_code == 422


def test_configured_interval_reports_overdue_before_the_first_meeting(
    client: TestClient, test_user: User
) -> None:
    response = client.put(
        "/api/v1/management-review/settings",
        json={
            "interval_months": 12,
            "start_date": (date.today() - timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["overdue"] is True
    assert body["next_due_date"] == (date.today() - timedelta(days=1)).isoformat()


def test_recording_a_meeting_advances_the_next_due_date(
    client: TestClient, test_user: User
) -> None:
    client.put(
        "/api/v1/management-review/settings",
        json={"interval_months": 6, "start_date": date.today().isoformat()},
    )

    created = client.post(
        "/api/v1/management-review/meetings",
        json={
            "meeting_date": date.today().isoformat(),
            "attendees": "CAIGO, AI System Owner, Risk Owner",
            "previous_actions_status": "All prior actions closed.",
            "context_changes": "No material change to internal/external issues.",
            "performance_summary": "No open nonconformities. All audits on schedule.",
            "stakeholder_feedback": "No complaints received this period.",
            "resource_adequacy": "Adequate for current AI system portfolio.",
            "improvement_opportunities": "Automate the quarterly metrics rollup.",
            "decisions_and_actions": "Approved budget for a new monitoring tool.",
        },
    )
    assert created.status_code == 201

    settings = client.get("/api/v1/management-review/settings").json()
    assert settings["overdue"] is False
    assert settings["next_due_date"] != date.today().isoformat()


def test_meeting_detail_round_trips_every_field(client: TestClient, test_user: User) -> None:
    created = client.post(
        "/api/v1/management-review/meetings",
        json={
            "meeting_date": date.today().isoformat(),
            "chaired_by": test_user.id,
            "attendees": "Everyone",
        },
    ).json()

    response = client.get(f"/api/v1/management-review/meetings/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["chaired_by"] == test_user.id
    assert body["attendees"] == "Everyone"
    assert body["framework_tags"] == []


def test_deleting_a_meeting_removes_it(client: TestClient, test_user: User) -> None:
    created = client.post(
        "/api/v1/management-review/meetings",
        json={"meeting_date": date.today().isoformat()},
    ).json()

    response = client.delete(f"/api/v1/management-review/meetings/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/v1/management-review/meetings/{created['id']}").status_code == 404


def test_uploading_meeting_minutes_as_evidence(client: TestClient, test_user: User) -> None:
    created = client.post(
        "/api/v1/management-review/meetings",
        json={"meeting_date": date.today().isoformat()},
    ).json()

    response = client.post(
        "/api/v1/evidence",
        data={"entity_type": "ManagementReviewMeeting", "entity_id": str(created["id"])},
        files={"file": ("minutes.pdf", b"file-bytes", "application/pdf")},
    )

    assert response.status_code == 201
    listed = client.get(
        "/api/v1/evidence",
        params={"entity_type": "ManagementReviewMeeting", "entity_id": created["id"]},
    ).json()
    assert len(listed) == 1
    assert listed[0]["filename"] == "minutes.pdf"
