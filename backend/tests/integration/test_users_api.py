from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models.user import User, UserRole


def test_directory_is_visible_to_any_logged_in_user(
    client: TestClient, make_user: Callable[..., User], login_as: Callable[[User], None]
) -> None:
    client.post(
        "/api/v1/users",
        json={"name": "Ada", "email": "ada@example.com", "password": "supersecret1"},
    )
    viewer = make_user(role=UserRole.VIEWER)
    login_as(viewer)

    response = client.get("/api/v1/users/directory")

    assert response.status_code == 200
    names = {entry["name"] for entry in response.json()}
    assert "Ada" in names
    # Directory entries expose id/name/governance_roles only -- not
    # email, role, or status.
    assert set(response.json()[0].keys()) == {"id", "name", "governance_roles"}


def test_admin_can_create_a_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/users",
        json={"name": "Ada", "email": "ada@example.com", "password": "supersecret1"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["role"] == "contributor"
    assert "password" not in body
    assert "password_hash" not in body


def test_admin_can_create_a_user_with_a_role(client: TestClient) -> None:
    response = client.post(
        "/api/v1/users",
        json={
            "name": "Ada",
            "email": "ada@example.com",
            "password": "supersecret1",
            "role": "viewer",
        },
    )

    assert response.json()["role"] == "viewer"


def test_admin_can_list_users(client: TestClient, test_user: User) -> None:
    client.post(
        "/api/v1/users",
        json={"name": "Ada", "email": "ada@example.com", "password": "supersecret1"},
    )

    response = client.get("/api/v1/users")

    emails = {u["email"] for u in response.json()}
    assert emails == {test_user.email, "ada@example.com"}


def test_non_admin_cannot_create_a_user(
    client: TestClient, make_user: Callable[..., User], login_as: Callable[[User], None]
) -> None:
    contributor = make_user(role=UserRole.CONTRIBUTOR)
    login_as(contributor)

    response = client.post(
        "/api/v1/users",
        json={"name": "Ada", "email": "ada@example.com", "password": "supersecret1"},
    )

    assert response.status_code == 403


def test_non_admin_cannot_list_users(
    client: TestClient, make_user: Callable[..., User], login_as: Callable[[User], None]
) -> None:
    viewer = make_user(role=UserRole.VIEWER)
    login_as(viewer)

    response = client.get("/api/v1/users")

    assert response.status_code == 403


def test_admin_can_change_another_users_role(
    client: TestClient, make_user: Callable[..., User]
) -> None:
    contributor = make_user(role=UserRole.CONTRIBUTOR)

    response = client.patch(f"/api/v1/users/{contributor.id}", json={"role": "admin"})

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_admin_can_deactivate_another_user(
    client: TestClient, make_user: Callable[..., User]
) -> None:
    contributor = make_user(role=UserRole.CONTRIBUTOR)

    response = client.patch(f"/api/v1/users/{contributor.id}", json={"is_active": False})

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_admin_cannot_change_their_own_role(client: TestClient, test_user: User) -> None:
    response = client.patch(f"/api/v1/users/{test_user.id}", json={"role": "viewer"})

    assert response.status_code == 409


def test_deactivated_user_loses_access_immediately(unauthenticated_client: TestClient) -> None:
    # Deliberately goes through the real cookie flow end to end (not the
    # login_as override, which replaces get_current_user outright and would
    # bypass the is_active check this test exists to exercise).
    unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"name": "Ada", "email": "ada@example.com", "password": "supersecret1"},
    )

    contributor = unauthenticated_client.post(
        "/api/v1/users",
        json={"name": "Bob", "email": "bob@example.com", "password": "supersecret1"},
    ).json()

    # A second browser session (fresh cookie jar, same app/db), logged in
    # as the contributor.
    from app.main import app

    contributor_client = TestClient(app)
    login_response = contributor_client.post(
        "/api/v1/auth/login", json={"email": "bob@example.com", "password": "supersecret1"}
    )
    assert login_response.status_code == 200
    # An administrator-chosen password is temporary: nothing works until it is replaced.
    assert contributor_client.get("/api/v1/policies").status_code == 403
    contributor_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "supersecret1", "new_password": "a-much-better-passphrase"},
    )
    assert contributor_client.get("/api/v1/policies").status_code == 200

    unauthenticated_client.patch(
        f"/api/v1/users/{contributor['id']}", json={"is_active": False}
    )

    # Same session cookie as before, no new login -- still blocked.
    response = contributor_client.get("/api/v1/policies")
    assert response.status_code == 401


def test_deactivated_user_cannot_log_in(unauthenticated_client: TestClient) -> None:
    unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"name": "Ada", "email": "ada@example.com", "password": "supersecret1"},
    )
    unauthenticated_client.cookies.clear()

    admin_login = unauthenticated_client.post(
        "/api/v1/auth/login", json={"email": "ada@example.com", "password": "supersecret1"}
    )
    assert admin_login.status_code == 200

    contributor = unauthenticated_client.post(
        "/api/v1/users",
        json={"name": "Bob", "email": "bob@example.com", "password": "supersecret1"},
    ).json()

    patch_response = unauthenticated_client.patch(
        f"/api/v1/users/{contributor['id']}", json={"is_active": False}
    )
    assert patch_response.status_code == 200

    unauthenticated_client.cookies.clear()
    login_response = unauthenticated_client.post(
        "/api/v1/auth/login", json={"email": "bob@example.com", "password": "supersecret1"}
    )

    assert login_response.status_code == 401
    assert "deactivated" in login_response.json()["detail"]
