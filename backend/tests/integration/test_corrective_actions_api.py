from collections.abc import Callable
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.user import User


def create_corrective_action(client: TestClient, **overrides) -> dict:
    payload = {
        "title": "Resume screener ranking drift",
        "nonconformity_description": "Model favors one demographic group in ranking.",
        "assignee_id": overrides.pop("assignee_id", None),
        "due_date": overrides.pop("due_date", (date.today() + timedelta(days=14)).isoformat()),
    }
    payload.update(overrides)
    response = client.post("/api/v1/corrective-actions", json=payload)
    assert response.status_code == 201
    return response.json()


def upload_evidence(client: TestClient, corrective_action_id: int) -> dict:
    response = client.post(
        "/api/v1/evidence",
        data={"entity_type": "CorrectiveAction", "entity_id": str(corrective_action_id)},
        files={"file": ("fix-report.pdf", b"file-bytes", "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()


def test_create_requires_assignee_and_due_date(client: TestClient, test_user: User) -> None:
    response = client.post(
        "/api/v1/corrective-actions",
        json={"title": "Missing fields", "nonconformity_description": "Something went wrong."},
    )

    assert response.status_code == 422


def test_create_and_get(client: TestClient, test_user: User) -> None:
    created = create_corrective_action(client, assignee_id=test_user.id)

    assert created["status"] == "open"
    assert created["assignee_id"] == test_user.id
    assert created["overdue"] is False

    response = client.get(f"/api/v1/corrective-actions/{created['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == "Resume screener ranking drift"


def test_past_due_date_is_reported_overdue(client: TestClient, test_user: User) -> None:
    created = create_corrective_action(
        client,
        assignee_id=test_user.id,
        due_date=(date.today() - timedelta(days=1)).isoformat(),
    )

    assert created["overdue"] is True


def test_moving_the_due_date_is_saved_and_audited(client: TestClient, test_user: User) -> None:
    """Regression: the date in the change set used to crash the audit log
    write, so the detail page's due-date picker returned a 500."""
    created = create_corrective_action(client, assignee_id=test_user.id)
    new_due_date = (date.today() + timedelta(days=30)).isoformat()

    response = client.put(
        f"/api/v1/corrective-actions/{created['id']}", json={"due_date": new_due_date}
    )

    assert response.status_code == 200
    assert response.json()["due_date"] == new_due_date
    entries = client.get(
        "/api/v1/audit-log",
        params={"entity_type": "CorrectiveAction", "entity_id": created["id"]},
    ).json()
    updated = next(entry for entry in entries if entry["action"] == "updated")
    assert updated["diff"] == {"due_date": new_due_date}


def test_cannot_edit_once_pending_verification(client: TestClient, test_user: User) -> None:
    created = create_corrective_action(client, assignee_id=test_user.id)
    ca_id = created["id"]
    client.put(f"/api/v1/corrective-actions/{ca_id}", json={"status": "in_progress"})
    client.put(
        f"/api/v1/corrective-actions/{ca_id}",
        json={"action_description": "Retrained the model on rebalanced data."},
    )
    upload_evidence(client, ca_id)

    submitted = client.post(f"/api/v1/corrective-actions/{ca_id}/submit-for-verification")
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "pending_verification"

    response = client.put(f"/api/v1/corrective-actions/{ca_id}", json={"title": "Edited"})
    assert response.status_code == 409


def test_submit_for_verification_requires_action_description(
    client: TestClient, test_user: User
) -> None:
    created = create_corrective_action(client, assignee_id=test_user.id)
    ca_id = created["id"]
    client.put(f"/api/v1/corrective-actions/{ca_id}", json={"status": "in_progress"})
    upload_evidence(client, ca_id)

    response = client.post(f"/api/v1/corrective-actions/{ca_id}/submit-for-verification")

    assert response.status_code == 400
    assert "action taken" in response.json()["detail"]


def test_submit_for_verification_requires_evidence(client: TestClient, test_user: User) -> None:
    created = create_corrective_action(client, assignee_id=test_user.id)
    ca_id = created["id"]
    client.put(f"/api/v1/corrective-actions/{ca_id}", json={"status": "in_progress"})
    client.put(
        f"/api/v1/corrective-actions/{ca_id}",
        json={"action_description": "Retrained the model."},
    )

    response = client.post(f"/api/v1/corrective-actions/{ca_id}/submit-for-verification")

    assert response.status_code == 400
    assert "evidence" in response.json()["detail"]


def _submit_for_verification(client: TestClient, ca_id: int) -> None:
    client.put(f"/api/v1/corrective-actions/{ca_id}", json={"status": "in_progress"})
    client.put(
        f"/api/v1/corrective-actions/{ca_id}",
        json={"action_description": "Retrained the model on rebalanced data."},
    )
    upload_evidence(client, ca_id)
    response = client.post(f"/api/v1/corrective-actions/{ca_id}/submit-for-verification")
    assert response.status_code == 200


def test_non_caigo_admin_cannot_verify_and_close(
    client: TestClient, test_user: User, second_user: User, login_as: Callable[[User], None]
) -> None:
    created = create_corrective_action(client, assignee_id=test_user.id)
    ca_id = created["id"]
    _submit_for_verification(client, ca_id)
    login_as(second_user)

    response = client.post(f"/api/v1/corrective-actions/{ca_id}/verify-and-close")

    assert response.status_code == 403


def test_cannot_verify_and_close_your_own_submission(
    client: TestClient, test_user: User, make_caigo: Callable[[User], None]
) -> None:
    make_caigo(test_user)
    created = create_corrective_action(client, assignee_id=test_user.id)
    ca_id = created["id"]
    _submit_for_verification(client, ca_id)

    response = client.post(f"/api/v1/corrective-actions/{ca_id}/verify-and-close")

    assert response.status_code == 409
    assert "same user" in response.json()["detail"]


def test_a_different_caigo_can_verify_and_close(
    client: TestClient,
    test_user: User,
    second_user: User,
    make_caigo: Callable[[User], None],
    login_as: Callable[[User], None],
) -> None:
    make_caigo(second_user)
    created = create_corrective_action(client, assignee_id=test_user.id)
    ca_id = created["id"]
    _submit_for_verification(client, ca_id)
    login_as(second_user)

    response = client.post(f"/api/v1/corrective-actions/{ca_id}/verify-and-close")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "closed"
    assert body["closed_by"] == second_user.id


def test_reopen_requires_verification_and_evidence_again(
    client: TestClient,
    test_user: User,
    second_user: User,
    make_caigo: Callable[[User], None],
    login_as: Callable[[User], None],
) -> None:
    make_caigo(second_user)
    created = create_corrective_action(client, assignee_id=test_user.id)
    ca_id = created["id"]
    _submit_for_verification(client, ca_id)
    login_as(second_user)
    client.post(f"/api/v1/corrective-actions/{ca_id}/verify-and-close")

    reopened = client.post(f"/api/v1/corrective-actions/{ca_id}/reopen")

    assert reopened.status_code == 200
    body = reopened.json()
    assert body["status"] == "in_progress"
    assert body["closed_by"] is None
    assert body["closed_at"] is None


def test_deleting_last_evidence_reopens_a_closed_corrective_action(
    client: TestClient,
    test_user: User,
    second_user: User,
    make_caigo: Callable[[User], None],
    login_as: Callable[[User], None],
) -> None:
    make_caigo(second_user)
    created = create_corrective_action(client, assignee_id=test_user.id)
    ca_id = created["id"]
    _submit_for_verification(client, ca_id)
    login_as(second_user)
    client.post(f"/api/v1/corrective-actions/{ca_id}/verify-and-close")

    evidence_list = client.get(
        "/api/v1/evidence", params={"entity_type": "CorrectiveAction", "entity_id": ca_id}
    ).json()
    for item in evidence_list:
        client.delete(f"/api/v1/evidence/{item['id']}")

    response = client.get(f"/api/v1/corrective-actions/{ca_id}")
    assert response.json()["status"] == "in_progress"


def test_only_an_open_corrective_action_can_be_deleted(
    client: TestClient, test_user: User
) -> None:
    created = create_corrective_action(client, assignee_id=test_user.id)
    ca_id = created["id"]
    client.put(f"/api/v1/corrective-actions/{ca_id}", json={"status": "in_progress"})

    response = client.delete(f"/api/v1/corrective-actions/{ca_id}")

    assert response.status_code == 409
