"""The Data Inventory review over the API: the assigned Data Owner submits a
dataset entry, the Chief AI Governance Officer approves it."""

from fastapi.testclient import TestClient

from app.models.user import UserRole

ROWS = "/api/v1/data-inventory/rows"


def create_dataset(client: TestClient, owner_id: int | None = None, **overrides) -> int:
    data = {"dataset_name": "Applicant CVs"}
    if owner_id is not None:
        data["data_owner"] = str(owner_id)
    data.update(overrides)
    response = client.post(ROWS, json={"data": data})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def record(client: TestClient, row_id: int) -> dict:
    response = client.get(f"{ROWS}/{row_id}/record")
    assert response.status_code == 200, response.text
    return response.json()


def pending(client: TestClient) -> list[dict]:
    return client.get("/api/v1/dashboard/summary").json()["pending_approvals"]


def test_a_new_dataset_is_reported_as_draft(client: TestClient) -> None:
    row_id = create_dataset(client)

    assert record(client, row_id)["status"] == "draft"


def test_the_full_owner_then_caigo_flow(
    client: TestClient, test_user, make_user, login_as, caigo_admin
) -> None:
    row_id = create_dataset(client, owner_id=test_user.id)

    submitted = client.post(f"{ROWS}/{row_id}/submit-for-approval")
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "pending_approval"
    assert submitted.json()["submitted_by"] == test_user.id

    login_as(caigo_admin)
    approved = client.post(f"{ROWS}/{row_id}/approve")
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["status"] == "approved"
    assert body["approved_by"] == caigo_admin.id
    assert body["approved_by_name"] == caigo_admin.name


def test_a_non_owner_cannot_edit_or_submit(
    client: TestClient, test_user, make_user, login_as
) -> None:
    row_id = create_dataset(client, owner_id=test_user.id)
    login_as(make_user(role=UserRole.CONTRIBUTOR))

    edit = client.put(f"{ROWS}/{row_id}", json={"data": {"data_type": "training"}})
    submit = client.post(f"{ROWS}/{row_id}/submit-for-approval")

    assert edit.status_code == 403
    assert submit.status_code == 403


def test_submitting_without_a_data_owner_is_rejected(client: TestClient) -> None:
    row_id = create_dataset(client)

    response = client.post(f"{ROWS}/{row_id}/submit-for-approval")

    assert response.status_code == 400
    assert record(client, row_id)["status"] == "draft"


def test_approving_requires_the_approve_permission(
    client: TestClient, test_user, make_user, login_as
) -> None:
    row_id = create_dataset(client, owner_id=test_user.id)
    client.post(f"{ROWS}/{row_id}/submit-for-approval")

    login_as(make_user(role=UserRole.CONTRIBUTOR))
    response = client.post(f"{ROWS}/{row_id}/approve")

    assert response.status_code == 403


def test_a_non_caigo_admin_cannot_approve(
    client: TestClient, test_user, make_user, login_as
) -> None:
    row_id = create_dataset(client, owner_id=test_user.id)
    client.post(f"{ROWS}/{row_id}/submit-for-approval")

    login_as(make_user(role=UserRole.ADMIN))
    response = client.post(f"{ROWS}/{row_id}/approve")

    assert response.status_code == 403


def test_the_submitter_cannot_approve_their_own_dataset(
    client: TestClient, caigo_admin, login_as
) -> None:
    login_as(caigo_admin)
    row_id = create_dataset(client, owner_id=caigo_admin.id)
    client.post(f"{ROWS}/{row_id}/submit-for-approval")

    response = client.post(f"{ROWS}/{row_id}/approve")

    assert response.status_code == 409
    assert "someone else" in response.json()["detail"]


def test_editing_an_approved_dataset_sends_it_back_to_draft(
    client: TestClient, test_user, login_as, caigo_admin
) -> None:
    row_id = create_dataset(client, owner_id=test_user.id)
    client.post(f"{ROWS}/{row_id}/submit-for-approval")
    login_as(caigo_admin)
    client.post(f"{ROWS}/{row_id}/approve")

    login_as(test_user)
    updated = client.put(f"{ROWS}/{row_id}", json={"data": {"data_source": "Portal"}})

    assert updated.status_code == 200
    assert updated.json()["data"]["approval_status"] == "draft"
    assert record(client, row_id)["status"] == "draft"


def test_caigo_sees_a_submitted_dataset_awaiting_approval(
    client: TestClient, test_user, make_user, login_as, caigo_admin
) -> None:
    row_id = create_dataset(client, owner_id=test_user.id)
    client.post(f"{ROWS}/{row_id}/submit-for-approval")

    login_as(caigo_admin)
    items = [item for item in pending(client) if item["entity_type"] == "DataInventory"]

    assert len(items) == 1
    assert items[0]["entity_id"] == row_id
    assert items[0]["title"] == "Applicant CVs"


def test_a_non_caigo_admin_sees_no_pending_datasets(
    client: TestClient, test_user, make_user, login_as
) -> None:
    row_id = create_dataset(client, owner_id=test_user.id)
    client.post(f"{ROWS}/{row_id}/submit-for-approval")

    login_as(make_user(role=UserRole.ADMIN))

    assert [i for i in pending(client) if i["entity_type"] == "DataInventory"] == []


def test_caigo_does_not_see_a_dataset_they_submitted_themselves(
    client: TestClient, caigo_admin, login_as
) -> None:
    login_as(caigo_admin)
    row_id = create_dataset(client, owner_id=caigo_admin.id)
    client.post(f"{ROWS}/{row_id}/submit-for-approval")

    assert [i for i in pending(client) if i["entity_type"] == "DataInventory"] == []


def test_the_review_trail_is_readable_across_every_dataset(
    client: TestClient, test_user, login_as, caigo_admin
) -> None:
    """A dataset's review is logged against its row id, so the sheet has no
    single id to look it up by -- the audit log has to be listable by entity
    type alone or the trail is recorded and unviewable."""
    row_id = create_dataset(client, owner_id=test_user.id)
    client.post(f"{ROWS}/{row_id}/submit-for-approval")
    login_as(caigo_admin)
    client.post(f"{ROWS}/{row_id}/approve")

    response = client.get("/api/v1/audit-log", params={"entity_type": "DataInventoryApproval"})

    assert response.status_code == 200
    actions = [entry["action"] for entry in response.json()]
    assert actions == ["submitted_for_review", "approved"]


def test_listing_by_entity_type_and_id_still_narrows_to_one_record(
    client: TestClient, test_user, login_as, caigo_admin
) -> None:
    first = create_dataset(client, owner_id=test_user.id, dataset_name="First")
    second = create_dataset(client, owner_id=test_user.id, dataset_name="Second")
    client.post(f"{ROWS}/{first}/submit-for-approval")
    client.post(f"{ROWS}/{second}/submit-for-approval")

    response = client.get(
        "/api/v1/audit-log",
        params={"entity_type": "DataInventoryApproval", "entity_id": first},
    )

    assert [entry["entity_id"] for entry in response.json()] == [first]
