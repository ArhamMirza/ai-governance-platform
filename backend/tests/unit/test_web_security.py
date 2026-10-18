"""The two middleware, exercised on a tiny app of their own so each rule is
tested without the rest of the platform in the way."""

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from app.core.web_security import (
    API_CONTENT_SECURITY_POLICY,
    HSTS_VALUE,
    OriginCheckMiddleware,
    SecurityHeadersMiddleware,
)

COOKIE = "session_token"
ALLOWED = ["https://governance.example.com", "http://localhost:5173/"]


def headers_app(**options) -> TestClient:
    app = FastAPI()

    @app.get("/api/v1/thing")
    def thing() -> dict:
        return {"ok": True}

    @app.get("/api/v1/custom")
    def custom(response: Response) -> dict:
        response.headers["Cache-Control"] = "private, max-age=60"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return {"ok": True}

    @app.get("/docs")
    def docs() -> dict:
        return {"docs": True}

    @app.get("/elsewhere")
    def elsewhere() -> dict:
        return {"ok": True}

    app.add_middleware(SecurityHeadersMiddleware, **{"hsts": False, **options})
    return TestClient(app)


def origin_app() -> TestClient:
    app = FastAPI()

    @app.post("/change")
    def change() -> dict:
        return {"changed": True}

    @app.get("/read")
    def read() -> dict:
        return {"read": True}

    @app.delete("/remove")
    def remove() -> dict:
        return {"removed": True}

    @app.put("/replace")
    def replace() -> dict:
        return {"replaced": True}

    @app.patch("/amend")
    def amend() -> dict:
        return {"amended": True}

    app.add_middleware(OriginCheckMiddleware, allowed_origins=ALLOWED, cookie_name=COOKIE)
    return TestClient(app)


# ---------- security headers ----------


def test_every_response_carries_the_protective_headers() -> None:
    response = headers_app().get("/api/v1/thing")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["content-security-policy"] == API_CONTENT_SECURITY_POLICY
    assert "camera=()" in response.headers["permissions-policy"]


def test_the_api_policy_forbids_everything_a_page_could_do() -> None:
    policy = API_CONTENT_SECURITY_POLICY

    for directive in (
        "default-src 'none'",
        "frame-ancestors 'none'",
        "sandbox",
        "form-action 'none'",
    ):
        assert directive in policy


def test_private_api_responses_are_not_cached_but_other_paths_are_left_alone() -> None:
    client = headers_app()

    assert client.get("/api/v1/thing").headers["cache-control"] == "no-store"
    assert "cache-control" not in client.get("/elsewhere").headers


def test_a_header_the_route_set_itself_is_not_overridden() -> None:
    response = headers_app().get("/api/v1/custom")

    assert response.headers["cache-control"] == "private, max-age=60"
    assert response.headers["x-frame-options"] == "SAMEORIGIN"
    # ...while the ones it did not set are still added.
    assert response.headers["x-content-type-options"] == "nosniff"


def test_strict_transport_security_only_when_the_site_is_https() -> None:
    assert "strict-transport-security" not in headers_app(hsts=False).get("/elsewhere").headers
    secure = headers_app(hsts=True).get("/elsewhere")
    assert secure.headers["strict-transport-security"] == HSTS_VALUE
    assert "max-age=31536000" in HSTS_VALUE and "includeSubDomains" in HSTS_VALUE
    assert "preload" not in HSTS_VALUE  # hard to undo; left as the operator's decision


def test_the_docs_pages_are_exempt_from_the_api_policy_only_when_listed() -> None:
    exempt = headers_app(csp_exempt_paths=("/docs", "/redoc"))
    strict = headers_app()

    assert "content-security-policy" not in exempt.get("/docs").headers
    # The exemption is for those paths alone.
    assert exempt.get("/api/v1/thing").headers["content-security-policy"]
    assert strict.get("/docs").headers["content-security-policy"] == API_CONTENT_SECURITY_POLICY
    # The other protections still apply on an exempt page.
    assert exempt.get("/docs").headers["x-content-type-options"] == "nosniff"


# ---------- cross-site requests ----------


def cookie(**extra: str) -> dict[str, str]:
    return {"Cookie": f"{COOKIE}=abc", **extra}


@pytest.mark.parametrize("origin", ["https://evil.example", "http://localhost:5174", "null"])
def test_a_change_from_another_site_with_a_session_is_refused(origin: str) -> None:
    response = origin_app().post("/change", headers=cookie(Origin=origin))

    assert response.status_code == 403
    assert "another website" in response.json()["detail"]


@pytest.mark.parametrize(
    ("method", "path"),
    [("post", "/change"), ("put", "/replace"), ("patch", "/amend"), ("delete", "/remove")],
)
def test_every_state_changing_method_is_checked(method: str, path: str) -> None:
    client = origin_app()

    refused = getattr(client, method)(path, headers=cookie(Origin="https://evil.example"))
    allowed = getattr(client, method)(path, headers=cookie(Origin="http://localhost:5173"))

    assert refused.status_code == 403
    assert allowed.status_code == 200


@pytest.mark.parametrize("origin", ["https://governance.example.com", "http://localhost:5173"])
def test_the_apps_own_origins_are_allowed_even_with_a_trailing_slash_in_config(
    origin: str,
) -> None:
    assert origin_app().post("/change", headers=cookie(Origin=origin)).status_code == 200


def test_an_origin_that_only_starts_like_an_allowed_one_is_refused() -> None:
    client = origin_app()

    for lookalike in (
        "https://governance.example.com.evil.net",
        "https://governance.example.com:8443",
        "http://governance.example.com",
    ):
        assert client.post("/change", headers=cookie(Origin=lookalike)).status_code == 403


def test_a_page_served_from_the_same_address_as_the_api_is_allowed() -> None:
    client = origin_app()

    response = client.post("/change", headers=cookie(Origin="http://testserver", Host="testserver"))

    assert response.status_code == 200
    # A different host in the origin is not "the same address".
    wrong = client.post("/change", headers=cookie(Origin="http://evil.example", Host="testserver"))
    assert wrong.status_code == 403


def test_reading_is_never_refused() -> None:
    response = origin_app().get("/read", headers=cookie(Origin="https://evil.example"))

    assert response.status_code == 200


def test_a_request_without_the_session_cookie_is_not_a_browser_session() -> None:
    # Sign-in has no cookie yet, and the browser extension uses a key.
    client = origin_app()

    assert client.post("/change", headers={"Origin": "https://evil.example"}).status_code == 200
    other = {"Cookie": "something_else=1", "Origin": "https://evil.example"}
    assert client.post("/change", headers=other).status_code == 200


def test_no_origin_means_not_a_browser_unless_the_browser_says_cross_site() -> None:
    client = origin_app()

    assert client.post("/change", headers=cookie()).status_code == 200
    assert (
        client.post("/change", headers=cookie(**{"Sec-Fetch-Site": "same-origin"})).status_code
        == 200
    )
    assert (
        client.post("/change", headers=cookie(**{"Sec-Fetch-Site": "cross-site"})).status_code
        == 403
    )


def test_a_malformed_cookie_header_that_names_the_session_is_still_checked() -> None:
    client = origin_app()
    headers = {"Cookie": f'{COOKIE}=abc; bad"value=;', "Origin": "https://evil.example"}

    assert client.post("/change", headers=headers).status_code == 403


@pytest.mark.parametrize(
    "header",
    [
        f"{COOKIE}=abc",
        f"theme=dark; {COOKIE}=abc; x=1",
        f"junk;{COOKIE}=abc",
        f"  {COOKIE} = abc ",
        f'a="unclosed; {COOKIE}=abc',
        f";;; ={COOKIE}; {COOKIE}=",
    ],
)
def test_the_session_cookie_is_found_however_the_header_is_laid_out(header: str) -> None:
    response = origin_app().post(
        "/change", headers={"Cookie": header, "Origin": "https://evil.example"}
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "header", [f"x{COOKIE}=abc", f"{COOKIE}x=abc", f"a={COOKIE}=1", f"{COOKIE.upper()}=abc", ""]
)
def test_other_cookies_do_not_count_as_the_session(header: str) -> None:
    response = origin_app().post(
        "/change", headers={"Cookie": header, "Origin": "https://evil.example"}
    )

    assert response.status_code == 200


def test_the_session_cookie_is_found_among_others() -> None:
    headers = {"Cookie": f"theme=dark; {COOKIE}=abc; x=1", "Origin": "https://evil.example"}

    assert origin_app().post("/change", headers=headers).status_code == 403


def test_the_host_prefixed_cookie_name_is_what_is_checked_on_https_deployments() -> None:
    app = FastAPI()

    @app.post("/change")
    def change() -> dict:
        return {"changed": True}

    app.add_middleware(OriginCheckMiddleware, allowed_origins=ALLOWED, cookie_name="__Host-session")
    client = TestClient(app)

    refused = client.post(
        "/change", headers={"Cookie": "__Host-session=abc", "Origin": "https://evil.example"}
    )
    ignored = client.post(
        "/change", headers={"Cookie": f"{COOKIE}=abc", "Origin": "https://evil.example"}
    )

    assert refused.status_code == 403
    assert ignored.status_code == 200
