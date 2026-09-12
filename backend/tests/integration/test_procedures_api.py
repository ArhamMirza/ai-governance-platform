from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models.user import User, UserRole


def create_procedure(client: TestClient, **overrides) -> dict:
    payload = {"title": "Model Validation Procedure"}
    payload.update(overrides)
    response = client.post("/api/v1/procedures", json=payload)
    assert response.status_code == 201
    return response.json()


def upload_document(client: TestClient, procedure_id: int, filename: str = "procedure.pdf") -> dict:
    response = client.post(
        "/api/v1/evidence",
        data={"entity_type": "Procedure", "entity_id": str(procedure_id)},
        files={"file": (filename, b"file-bytes", "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()


def test_create_and_get_procedure(client: TestClient) -> None:
    created = create_procedure(client)

    assert created["status"] == "draft"
    assert created["version"] == 1
    assert created["policy_id"] is None

    response = client.get(f"/api/v1/procedures/{created['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == "Model Validation Procedure"


def test_get_missing_procedure_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/procedures/999")
    assert response.status_code == 404


def test_list_procedures(client: TestClient) -> None:
    create_procedure(client, title="Procedure A")
    create_procedure(client, title="Procedure B")

    response = client.get("/api/v1/procedures")

    assert response.status_code == 200
    titles = {p["title"] for p in response.json()}
    assert titles == {"Procedure A", "Procedure B"}


def test_create_procedure_linked_to_policy(client: TestClient) -> None:
    policy = client.post("/api/v1/policies", json={"title": "Data Retention Policy"}).json()

    created = create_procedure(client, policy_id=policy["id"])

    assert created["policy_id"] == policy["id"]


def test_create_procedure_rejects_missing_policy_link(client: TestClient) -> None:
    response = client.post(
        "/api/v1/procedures", json={"title": "Orphan Procedure", "policy_id": 999}
    )

    assert response.status_code == 404


def test_update_procedure_metadata_does_not_bump_version(client: TestClient) -> None:
    created = create_procedure(client)

    response = client.put(
        f"/api/v1/procedures/{created['id']}", json={"title": "Renamed Procedure"}
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Renamed Procedure"
    assert response.json()["version"] == 1


def test_update_procedure_can_set_owner(client: TestClient, second_user: User) -> None:
    procedure_id = create_procedure(client)["id"]

    response = client.put(
        f"/api/v1/procedures/{procedure_id}", json={"owner_id": second_user.id}
    )

    assert response.status_code == 200
    assert response.json()["owner_id"] == second_user.id


def test_uploading_a_document_bumps_version_and_appears_in_history(client: TestClient) -> None:
    procedure_id = create_procedure(client)["id"]

    upload_document(client, procedure_id, filename="procedure-draft.pdf")

    updated = client.get(f"/api/v1/procedures/{procedure_id}").json()
    assert updated["version"] == 2

    history = client.get(f"/api/v1/procedures/{procedure_id}/versions").json()
    assert len(history) == 1
    assert history[0]["action"] == "document_added"
    assert history[0]["diff"]["filename"] == "procedure-draft.pdf"


def test_full_review_workflow(
    client: TestClient,
    second_user: User,
    login_as: Callable[[User], None],
    make_caigo: Callable[[User], None],
) -> None:
    procedure_id = create_procedure(client)["id"]

    submit_response = client.post(f"/api/v1/procedures/{procedure_id}/submit-for-review")
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "in_review"

    make_caigo(second_user)
    login_as(second_user)
    approve_response = client.post(f"/api/v1/procedures/{procedure_id}/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"


def test_cannot_approve_a_draft_procedure(
    client: TestClient, second_user: User, login_as: Callable[[User], None]
) -> None:
    procedure_id = create_procedure(client)["id"]
    login_as(second_user)

    response = client.post(f"/api/v1/procedures/{procedure_id}/approve")

    assert response.status_code == 409


def test_cannot_approve_your_own_submission(
    client: TestClient, test_user: User, make_caigo: Callable[[User], None]
) -> None:
    make_caigo(test_user)
    procedure_id = create_procedure(client)["id"]
    client.post(f"/api/v1/procedures/{procedure_id}/submit-for-review")

    response = client.post(f"/api/v1/procedures/{procedure_id}/approve")

    assert response.status_code == 409
    assert "same user" in response.json()["detail"]


def test_non_caigo_admin_cannot_approve(
    client: TestClient, second_user: User, login_as: Callable[[User], None]
) -> None:
    procedure_id = create_procedure(client)["id"]
    client.post(f"/api/v1/procedures/{procedure_id}/submit-for-review")
    login_as(second_user)

    response = client.post(f"/api/v1/procedures/{procedure_id}/approve")

    assert response.status_code == 403


def test_cannot_edit_after_submitted_for_review(client: TestClient) -> None:
    procedure_id = create_procedure(client)["id"]
    client.post(f"/api/v1/procedures/{procedure_id}/submit-for-review")

    response = client.put(f"/api/v1/procedures/{procedure_id}", json={"title": "sneaky edit"})

    assert response.status_code == 409


def test_delete_draft_procedure(client: TestClient) -> None:
    procedure_id = create_procedure(client)["id"]

    response = client.delete(f"/api/v1/procedures/{procedure_id}")
    assert response.status_code == 204

    assert client.get(f"/api/v1/procedures/{procedure_id}").status_code == 404


def test_cannot_delete_approved_procedure(
    client: TestClient,
    second_user: User,
    login_as: Callable[[User], None],
    make_caigo: Callable[[User], None],
) -> None:
    procedure_id = create_procedure(client)["id"]
    client.post(f"/api/v1/procedures/{procedure_id}/submit-for-review")
    make_caigo(second_user)
    login_as(second_user)
    assert client.post(f"/api/v1/procedures/{procedure_id}/approve").status_code == 200

    response = client.delete(f"/api/v1/procedures/{procedure_id}")

    assert response.status_code == 409


def approved_procedure(
    client: TestClient,
    second_user: User,
    login_as: Callable[[User], None],
    make_caigo: Callable[[User], None],
) -> int:
    procedure_id = create_procedure(client)["id"]
    client.post(f"/api/v1/procedures/{procedure_id}/submit-for-review")
    make_caigo(second_user)
    login_as(second_user)
    assert client.post(f"/api/v1/procedures/{procedure_id}/approve").status_code == 200
    return procedure_id


def test_approval_schedules_the_next_review(
    client: TestClient,
    second_user: User,
    login_as: Callable[[User], None],
    make_caigo: Callable[[User], None],
) -> None:
    procedure_id = approved_procedure(client, second_user, login_as, make_caigo)

    body = client.get(f"/api/v1/procedures/{procedure_id}").json()

    assert body["next_review_date"] is not None


def test_retiring_requires_an_approved_procedure(
    client: TestClient,
    second_user: User,
    login_as: Callable[[User], None],
    make_caigo: Callable[[User], None],
) -> None:
    procedure_id = create_procedure(client)["id"]
    make_caigo(second_user)
    login_as(second_user)

    response = client.post(f"/api/v1/procedures/{procedure_id}/retire")

    assert response.status_code == 409


def test_a_non_caigo_admin_cannot_retire(
    client: TestClient,
    second_user: User,
    login_as: Callable[[User], None],
    make_caigo: Callable[[User], None],
    make_user,
) -> None:
    procedure_id = approved_procedure(client, second_user, login_as, make_caigo)
    login_as(make_user(role=UserRole.ADMIN))

    response = client.post(f"/api/v1/procedures/{procedure_id}/retire")

    assert response.status_code == 403


def test_retiring_requires_the_approve_permission(
    client: TestClient,
    second_user: User,
    login_as: Callable[[User], None],
    make_caigo: Callable[[User], None],
    make_user,
) -> None:
    procedure_id = approved_procedure(client, second_user, login_as, make_caigo)
    login_as(make_user(role=UserRole.CONTRIBUTOR))

    response = client.post(f"/api/v1/procedures/{procedure_id}/retire")

    assert response.status_code == 403


def test_caigo_can_retire_a_superseded_procedure(
    client: TestClient,
    second_user: User,
    login_as: Callable[[User], None],
    make_caigo: Callable[[User], None],
) -> None:
    procedure_id = approved_procedure(client, second_user, login_as, make_caigo)

    response = client.post(f"/api/v1/procedures/{procedure_id}/retire")

    assert response.status_code == 200
    assert response.json()["status"] == "retired"


def test_a_retired_procedure_leaves_the_coverage_ratio(
    client: TestClient,
    second_user: User,
    login_as: Callable[[User], None],
    make_caigo: Callable[[User], None],
) -> None:
    procedure_id = approved_procedure(client, second_user, login_as, make_caigo)
    assert client.get("/api/v1/dashboard/summary").json()["coverage"]["procedures_total"] == 1

    client.post(f"/api/v1/procedures/{procedure_id}/retire")

    coverage = client.get("/api/v1/dashboard/summary").json()["coverage"]
    assert coverage["procedures_total"] == 0
