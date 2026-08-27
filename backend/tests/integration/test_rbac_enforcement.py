"""Spot-checks that role enforcement actually reaches real routes, on top of
the unit coverage in test_permissions.py. Not exhaustive over every mutating
endpoint -- get_current_actor_id is one shared dependency, so these confirm
the wiring rather than re-testing has_permission() per route."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models.user import User, UserRole


def test_viewer_can_read(
    client: TestClient, make_user: Callable[..., User], login_as: Callable[[User], None]
) -> None:
    viewer = make_user(role=UserRole.VIEWER)
    login_as(viewer)

    response = client.get("/api/v1/policies")

    assert response.status_code == 200


def test_viewer_cannot_create_a_policy(
    client: TestClient, make_user: Callable[..., User], login_as: Callable[[User], None]
) -> None:
    viewer = make_user(role=UserRole.VIEWER)
    login_as(viewer)

    response = client.post("/api/v1/policies", json={"title": "Sneaky Policy"})

    assert response.status_code == 403


def test_viewer_cannot_upload_evidence(
    client: TestClient, make_user: Callable[..., User], login_as: Callable[[User], None]
) -> None:
    policy = client.post("/api/v1/policies", json={"title": "Data Retention Policy"}).json()
    viewer = make_user(role=UserRole.VIEWER)
    login_as(viewer)

    response = client.post(
        "/api/v1/evidence",
        data={"entity_type": "Policy", "entity_id": str(policy["id"])},
        files={"file": ("policy.pdf", b"bytes", "application/pdf")},
    )

    assert response.status_code == 403


def test_contributor_can_create_a_policy(
    client: TestClient, make_user: Callable[..., User], login_as: Callable[[User], None]
) -> None:
    contributor = make_user(role=UserRole.CONTRIBUTOR)
    login_as(contributor)

    response = client.post("/api/v1/policies", json={"title": "Vendor Policy"})

    assert response.status_code == 201


def test_contributor_can_submit_for_review(
    client: TestClient, make_user: Callable[..., User], login_as: Callable[[User], None]
) -> None:
    contributor = make_user(role=UserRole.CONTRIBUTOR)
    login_as(contributor)
    policy_id = client.post("/api/v1/policies", json={"title": "Vendor Policy"}).json()["id"]

    response = client.post(f"/api/v1/policies/{policy_id}/submit-for-review")

    assert response.status_code == 200


def test_contributor_cannot_approve(
    client: TestClient, make_user: Callable[..., User], login_as: Callable[[User], None]
) -> None:
    contributor = make_user(role=UserRole.CONTRIBUTOR)
    login_as(contributor)
    policy_id = client.post("/api/v1/policies", json={"title": "Vendor Policy"}).json()["id"]
    client.post(f"/api/v1/policies/{policy_id}/submit-for-review")

    response = client.post(f"/api/v1/policies/{policy_id}/approve")

    assert response.status_code == 403


def test_contributor_cannot_change_risk_criteria(
    client: TestClient, make_user: Callable[..., User], login_as: Callable[[User], None]
) -> None:
    contributor = make_user(role=UserRole.CONTRIBUTOR)
    login_as(contributor)

    response = client.put(
        "/api/v1/risk-criteria", json={"medium_min_score": 4, "high_min_score": 10}
    )

    assert response.status_code == 403


def test_admin_can_change_risk_criteria(client: TestClient) -> None:
    response = client.put(
        "/api/v1/risk-criteria", json={"medium_min_score": 4, "high_min_score": 10}
    )

    assert response.status_code == 200


def test_viewer_can_still_read_risk_criteria(
    client: TestClient, make_user: Callable[..., User], login_as: Callable[[User], None]
) -> None:
    viewer = make_user(role=UserRole.VIEWER)
    login_as(viewer)

    response = client.get("/api/v1/risk-criteria")

    assert response.status_code == 200
