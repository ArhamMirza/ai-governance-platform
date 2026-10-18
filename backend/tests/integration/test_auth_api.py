from fastapi.testclient import TestClient


def test_registration_open_before_any_user_exists(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/api/v1/auth/registration-status")

    assert response.status_code == 200
    assert response.json() == {"registration_open": True, "setup_code_required": False}


def test_register_sets_a_session_cookie_and_returns_the_user(
    unauthenticated_client: TestClient,
) -> None:
    response = unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"name": "Ada Lovelace", "email": "ada@example.com", "password": "supersecret1"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert "password" not in body
    assert "password_hash" not in body
    assert "session_token" in response.cookies


def test_registration_closes_after_the_first_user(unauthenticated_client: TestClient) -> None:
    unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"name": "Ada Lovelace", "email": "ada@example.com", "password": "supersecret1"},
    )

    status = unauthenticated_client.get("/api/v1/auth/registration-status")
    assert status.json() == {"registration_open": False, "setup_code_required": False}

    second = unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"name": "Bob", "email": "bob@example.com", "password": "supersecret1"},
    )
    assert second.status_code == 409


def test_login_with_correct_credentials(unauthenticated_client: TestClient) -> None:
    unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"name": "Ada Lovelace", "email": "ada@example.com", "password": "supersecret1"},
    )
    unauthenticated_client.cookies.clear()

    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": "supersecret1"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "ada@example.com"
    assert "session_token" in response.cookies


def test_login_with_wrong_password(unauthenticated_client: TestClient) -> None:
    unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"name": "Ada Lovelace", "email": "ada@example.com", "password": "supersecret1"},
    )
    unauthenticated_client.cookies.clear()

    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": "wrong"},
    )

    assert response.status_code == 401


def test_me_without_a_session_is_401(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_with_a_session(unauthenticated_client: TestClient) -> None:
    unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"name": "Ada Lovelace", "email": "ada@example.com", "password": "supersecret1"},
    )

    response = unauthenticated_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "ada@example.com"


def test_logout_clears_the_session(unauthenticated_client: TestClient) -> None:
    unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"name": "Ada Lovelace", "email": "ada@example.com", "password": "supersecret1"},
    )

    logout_response = unauthenticated_client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    me_response = unauthenticated_client.get("/api/v1/auth/me")
    assert me_response.status_code == 401


def test_a_protected_read_route_requires_a_session(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/api/v1/policies")

    assert response.status_code == 401


def test_a_protected_write_route_requires_a_session(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.post("/api/v1/policies", json={"title": "Test Policy"})

    assert response.status_code == 401


def test_health_does_not_require_a_session(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/api/v1/health")

    assert response.status_code == 200


def test_logged_in_user_can_reach_protected_routes(unauthenticated_client: TestClient) -> None:
    unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"name": "Ada Lovelace", "email": "ada@example.com", "password": "supersecret1"},
    )

    response = unauthenticated_client.get("/api/v1/policies")

    assert response.status_code == 200


def test_writes_by_a_logged_in_user_are_attributed_in_the_audit_log(
    unauthenticated_client: TestClient,
) -> None:
    user = unauthenticated_client.post(
        "/api/v1/auth/register",
        json={"name": "Ada Lovelace", "email": "ada@example.com", "password": "supersecret1"},
    ).json()

    policy = unauthenticated_client.post(
        "/api/v1/policies", json={"title": "Test Policy"}
    ).json()

    history = unauthenticated_client.get(
        "/api/v1/audit-log", params={"entity_type": "Policy", "entity_id": policy["id"]}
    ).json()
    assert history[0]["actor_id"] == user["id"]
