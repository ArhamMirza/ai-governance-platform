"""HTTP-level protections that apply to every response and request.

Written as plain ASGI middleware (not BaseHTTPMiddleware) so streaming and
file responses are passed through untouched.
"""

from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# The API only ever returns JSON or a download, so nothing it sends should ever
# be rendered or run as a page. `sandbox` matters for downloads: an uploaded
# file served with a type the browser would render (HTML, SVG) is inert, with
# no scripts and no access to this origin, even if someone opens it directly.
API_CONTENT_SECURITY_POLICY = (
    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'; sandbox"
)
HSTS_VALUE = "max-age=31536000; includeSubDomains"
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class SecurityHeadersMiddleware:
    """Adds the standard protective headers to every HTTP response.

    A header the route already set is left alone, so a handler that has a
    reason to differ (a download with its own caching) is not overridden.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        hsts: bool,
        csp_exempt_paths: tuple[str, ...] = (),
    ) -> None:
        self.app = app
        self.hsts = hsts
        self.csp_exempt_paths = csp_exempt_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "no-referrer")
                headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
                if not path.startswith(self.csp_exempt_paths):
                    headers.setdefault("Content-Security-Policy", API_CONTENT_SECURITY_POLICY)
                if path.startswith("/api/"):
                    # Private data: nothing here may be kept by a browser or a proxy.
                    headers.setdefault("Cache-Control", "no-store")
                if self.hsts:
                    headers.setdefault("Strict-Transport-Security", HSTS_VALUE)
            await send(message)

        await self.app(scope, receive, send_with_headers)


class OriginCheckMiddleware:
    """Refuses a state-changing request that comes from another website.

    The session cookie is SameSite=Strict, which already keeps a browser from
    sending it cross-site; this is the second layer. A request that carries
    the session cookie and changes something must either have no Origin header
    (not a browser: curl, a script) or an Origin that is one of the app's own.
    Requests without the cookie -- sign-in, and the browser extension, which
    uses a key -- are not browser sessions and are not checked.
    """

    def __init__(self, app: ASGIApp, *, allowed_origins: list[str], cookie_name: str) -> None:
        self.app = app
        self.allowed_origins = frozenset(origin.rstrip("/") for origin in allowed_origins)
        self.cookie_name = cookie_name

    def _has_session_cookie(self, headers: Headers) -> bool:
        # Read the way the framework itself reads cookies (split on ";", name
        # before the first "="), so whatever it will treat as the session
        # cookie is also what is checked here, however mangled the rest is.
        raw = headers.get("cookie", "")
        return any(part.split("=", 1)[0].strip() == self.cookie_name for part in raw.split(";"))

    def _is_own_origin(self, origin: str, host: str | None) -> bool:
        if origin in self.allowed_origins:
            return True
        # Served from one address (the app and the API together): the origin's
        # host is the host the request was addressed to.
        return host is not None and urlsplit(origin).netloc == host

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _UNSAFE_METHODS:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        if self._has_session_cookie(headers):
            origin = headers.get("origin")
            foreign = (
                not self._is_own_origin(origin, headers.get("host"))
                if origin is not None
                else headers.get("sec-fetch-site") == "cross-site"
            )
            if foreign:
                response = JSONResponse(
                    {"detail": "This request came from another website and was refused."},
                    status_code=403,
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
