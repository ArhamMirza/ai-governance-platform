"""The protections as the real app applies them: headers on real responses,
the session cookie's attributes, cross-site requests, CORS, the first-run
setup code, and a production start-up."""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core import setup_code
from app.services import auth_service

API = "/api/v1"
ADA = {"name": "Ada Admin", "email": "ada@example.com", "password": "tangerine-lantern-47"}
ALLOWED_ORIGIN = "http://localhost:5173"
BACKEND = Path(__file__).resolve().parents[2]


def register(client: TestClient, **extra):
    return client.post(f"{API}/auth/register", json={**ADA, **extra})


# ---------- headers on real responses ----------


def test_real_responses_carry_the_protective_headers(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get(f"{API}/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert "default-src 'none'" in response.headers["content-security-policy"]


def test_an_error_response_carries_them_too(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get(f"{API}/policies")

    assert response.status_code == 401
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"


def test_a_refusal_for_a_cross_site_request_still_has_the_headers(
    unauthenticated_client: TestClient,
) -> None:
    register(unauthenticated_client)

    response = unauthenticated_client.post(
        f"{API}/policies", json={"title": "x"}, headers={"Origin": "https://evil.example"}
    )

    assert response.status_code == 403
    assert response.headers["x-content-type-options"] == "nosniff"


def test_an_uploaded_file_cannot_run_or_be_sniffed_when_downloaded(client: TestClient) -> None:
    uploaded = client.post(
        f"{API}/evidence",
        data={"entity_type": "Policy", "entity_id": "1"},
        files={"file": ("page.pdf", b"<script>alert(1)</script>", "text/html")},
    ).json()

    response = client.get(f"{API}/evidence/{uploaded['id']}/download")

    assert response.headers["content-disposition"].startswith("attachment")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in response.headers["content-security-policy"]
    assert "script-src" not in response.headers["content-security-policy"]


# ---------- the session cookie ----------


def test_the_session_cookie_is_httponly_and_strictly_same_site(
    unauthenticated_client: TestClient,
) -> None:
    response = register(unauthenticated_client)

    cookie = response.headers["set-cookie"]
    assert "session_token=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/" in cookie
    assert "Domain" not in cookie


def test_logging_out_clears_the_cookie_with_the_same_attributes(
    unauthenticated_client: TestClient,
) -> None:
    register(unauthenticated_client)

    response = unauthenticated_client.post(f"{API}/auth/logout")

    cleared = response.headers["set-cookie"]
    assert "session_token=" in cleared and "Max-Age=0" in cleared
    assert "HttpOnly" in cleared and "SameSite=strict" in cleared


# ---------- cross-site requests ----------


def test_a_change_from_another_site_is_refused_and_does_nothing(
    unauthenticated_client: TestClient,
) -> None:
    register(unauthenticated_client)

    refused = unauthenticated_client.post(
        f"{API}/policies", json={"title": "Planted"}, headers={"Origin": "https://evil.example"}
    )
    listed = unauthenticated_client.get(f"{API}/policies").json()

    assert refused.status_code == 403
    assert listed == []


def test_the_same_change_from_the_apps_own_origin_works(
    unauthenticated_client: TestClient,
) -> None:
    register(unauthenticated_client)

    response = unauthenticated_client.post(
        f"{API}/policies", json={"title": "Real"}, headers={"Origin": ALLOWED_ORIGIN}
    )

    assert response.status_code == 201


def test_signing_in_is_not_blocked_by_the_check(unauthenticated_client: TestClient) -> None:
    register(unauthenticated_client)
    unauthenticated_client.cookies.clear()

    response = unauthenticated_client.post(
        f"{API}/auth/login",
        json={"email": ADA["email"], "password": ADA["password"]},
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 200


# ---------- CORS ----------


def preflight(client: TestClient, method: str, headers: str, origin: str = ALLOWED_ORIGIN):
    return client.options(
        f"{API}/policies",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )


def test_cors_allows_only_the_methods_and_headers_the_app_uses(
    unauthenticated_client: TestClient,
) -> None:
    ok = preflight(unauthenticated_client, "PATCH", "content-type")
    assert ok.status_code == 200
    assert ok.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert ok.headers["access-control-allow-credentials"] == "true"

    assert preflight(unauthenticated_client, "TRACE", "content-type").status_code == 400
    assert preflight(unauthenticated_client, "HEAD", "content-type").status_code == 400
    assert preflight(unauthenticated_client, "POST", "x-evil-header").status_code == 400


def test_cors_does_not_trust_other_origins(unauthenticated_client: TestClient) -> None:
    response = preflight(unauthenticated_client, "POST", "content-type", "https://evil.example")

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_the_extensions_headers_are_allowed(unauthenticated_client: TestClient) -> None:
    response = preflight(unauthenticated_client, "GET", "authorization, if-none-match")

    assert response.status_code == 200


# ---------- the first-run setup code ----------


@pytest.fixture()
def real_deployment(monkeypatch: pytest.MonkeyPatch):
    """A server that says it is a real deployment, with a code of its own."""
    fake = SimpleNamespace(is_real_deployment=True, setup_code="letmein-first-run")
    monkeypatch.setattr(setup_code, "get_settings", lambda: fake)
    monkeypatch.setattr(setup_code, "_generated", None)
    return fake


def test_a_real_deployment_asks_for_the_setup_code(
    unauthenticated_client: TestClient, real_deployment
) -> None:
    status = unauthenticated_client.get(f"{API}/auth/registration-status").json()

    assert status == {"registration_open": True, "setup_code_required": True}


def test_without_the_code_no_account_is_made(
    unauthenticated_client: TestClient, real_deployment
) -> None:
    missing = register(unauthenticated_client)
    wrong = register(unauthenticated_client, setup_code="guess")

    assert missing.status_code == wrong.status_code == 400
    assert "setup code" in missing.json()["detail"]
    status = unauthenticated_client.get(f"{API}/auth/registration-status").json()
    assert status["registration_open"] is True


def test_the_right_code_creates_the_first_account(
    unauthenticated_client: TestClient, real_deployment
) -> None:
    response = register(unauthenticated_client, setup_code="  letmein-first-run  ")

    assert response.status_code == 201
    # ...and the code is not asked for again once an account exists.
    status = unauthenticated_client.get(f"{API}/auth/registration-status").json()
    assert status == {"registration_open": False, "setup_code_required": False}


def test_guessing_the_setup_code_is_limited(
    unauthenticated_client: TestClient, real_deployment
) -> None:
    for _ in range(5):
        assert register(unauthenticated_client, setup_code="nope").status_code == 400

    locked = register(unauthenticated_client, setup_code="nope")
    right = register(unauthenticated_client, setup_code="letmein-first-run")

    assert locked.status_code == right.status_code == 429


def test_a_closed_registration_stays_closed_whatever_the_code(
    unauthenticated_client: TestClient, real_deployment
) -> None:
    register(unauthenticated_client, setup_code="letmein-first-run")

    again = register(
        unauthenticated_client, email="second@example.com", setup_code="letmein-first-run"
    )

    assert again.status_code == 409


def test_development_needs_no_code(unauthenticated_client: TestClient) -> None:
    assert register(unauthenticated_client).status_code == 201


def test_the_registration_check_happens_before_the_code_is_counted(
    unauthenticated_client: TestClient, real_deployment
) -> None:
    register(unauthenticated_client, setup_code="letmein-first-run")
    for _ in range(8):
        assert register(unauthenticated_client, setup_code="wrong").status_code == 409

    # A closed door is not a guessing game: nothing was counted against the address.
    auth_service.reset_rate_limits()


# ---------- production start-up ----------


def test_a_production_start_has_no_docs_secure_cookies_and_hsts(tmp_path: Path) -> None:
    script = (
        "from fastapi.testclient import TestClient\n"
        "import app.main as m\n"
        "c = TestClient(m.app)\n"
        "r = c.get('/api/v1/health')\n"
        "print(c.get('/docs').status_code, c.get('/openapi.json').status_code, "
        "c.get('/redoc').status_code)\n"
        "print(r.headers.get('strict-transport-security'))\n"
        "print(m.settings.session_cookie_name)\n"
        "print(c.get('/docs').headers.get('content-security-policy'))\n"
    )
    env = {
        **os.environ,
        "ENVIRONMENT": "production",
        "SECRET_KEY": "a-secret-of-its-own-for-this-test",
        "COOKIE_SECURE": "true",
        "DATABASE_URL": f"sqlite:///{tmp_path / 'p.db'}",
    }

    done = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert done.returncode == 0, done.stderr
    lines = done.stdout.split("\n")
    assert lines[0] == "404 404 404"
    assert lines[1] == "max-age=31536000; includeSubDomains"
    assert lines[2] == "__Host-session"
    # Even the missing docs page gets the strict policy: nothing is exempt.
    assert "default-src 'none'" in lines[3]


def test_development_keeps_the_docs_with_their_own_policy(
    unauthenticated_client: TestClient,
) -> None:
    docs = unauthenticated_client.get("/docs")

    assert docs.status_code == 200
    assert "content-security-policy" not in docs.headers
    assert docs.headers["x-content-type-options"] == "nosniff"
