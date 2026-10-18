"""The short-lived proof that the password step of a two-step sign-in is done.

After a correct password, an account with two-step sign-in gets no session,
only this ticket; presenting it with a correct code is what yields the session.
It is signed (HMAC-SHA256, keyed from the deployment secret), carries nothing
secret, and is good for five minutes.

It is also tied to the password it was issued for: if the password changes
between the two steps the ticket stops working.
"""

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from app.core.config import get_settings

TTL_SECONDS = 300
_MAX_LENGTH = 400


@dataclass(frozen=True)
class Ticket:
    user_id: int
    password_fingerprint: str


def _key() -> bytes:
    return hashlib.sha256(b"two-step-ticket:" + get_settings().secret_key.encode()).digest()


def fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(body: str) -> str:
    return _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest())


def issue(user_id: int, password_hash: str, *, now: float | None = None) -> str:
    issued = time.time() if now is None else now
    payload = {"u": user_id, "e": int(issued) + TTL_SECONDS, "p": fingerprint(password_hash)}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    return f"{body}.{_sign(body)}"


def read(ticket: str, *, now: float | None = None) -> Ticket | None:
    """The ticket's contents, or None if it is forged, mangled or expired."""
    if not ticket or len(ticket) > _MAX_LENGTH or ticket.count(".") != 1:
        return None
    body, signature = ticket.split(".")
    if not hmac.compare_digest(signature, _sign(body)):
        return None
    try:
        payload = json.loads(_unb64(body))
        user_id, expires, password = int(payload["u"]), int(payload["e"]), str(payload["p"])
    except (ValueError, KeyError, TypeError):
        return None
    current = time.time() if now is None else now
    if current >= expires:
        return None
    return Ticket(user_id=user_id, password_fingerprint=password)
