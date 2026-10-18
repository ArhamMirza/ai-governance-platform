import base64
import json
from types import SimpleNamespace

import pytest

from app.core import mfa_ticket

NOW = 1_700_000_000.0


def test_a_ticket_reads_back_what_it_was_issued_for() -> None:
    ticket = mfa_ticket.issue(42, "pbkdf2$hash", now=NOW)

    read = mfa_ticket.read(ticket, now=NOW + 10)

    assert read == mfa_ticket.Ticket(
        user_id=42, password_fingerprint=mfa_ticket.fingerprint("pbkdf2$hash")
    )


def test_it_is_good_for_five_minutes_exactly() -> None:
    ticket = mfa_ticket.issue(1, "h", now=NOW)

    assert mfa_ticket.read(ticket, now=NOW + 299) is not None
    assert mfa_ticket.read(ticket, now=NOW + 300) is None
    assert mfa_ticket.read(ticket, now=NOW + 3600) is None


def test_it_does_not_contain_the_password_hash() -> None:
    ticket = mfa_ticket.issue(1, "secret-hash-value", now=NOW)

    assert "secret-hash-value" not in ticket
    assert "secret-hash-value" not in base64.urlsafe_b64decode(ticket.split(".")[0] + "==").decode()


def test_the_fingerprint_changes_with_the_password() -> None:
    assert mfa_ticket.fingerprint("one") != mfa_ticket.fingerprint("two")
    assert mfa_ticket.fingerprint("one") == mfa_ticket.fingerprint("one")


def forge(payload: dict, signature: str | None = None) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{body}.{signature or 'AAAA'}"


@pytest.mark.parametrize(
    "bad",
    ["", "x", "a.b.c", ".", "abc.", ".abc", "not-base64!.also-not", "a" * 500, "a.b" + "c" * 500],
)
def test_garbage_is_not_a_ticket(bad: str) -> None:
    assert mfa_ticket.read(bad, now=NOW) is None


def test_changing_the_user_in_a_ticket_breaks_the_signature() -> None:
    ticket = mfa_ticket.issue(1, "h", now=NOW)
    _, signature = ticket.split(".")
    forged = forge({"u": 2, "e": int(NOW) + 300, "p": mfa_ticket.fingerprint("h")}, signature)

    assert mfa_ticket.read(forged, now=NOW) is None


def test_extending_the_expiry_breaks_the_signature() -> None:
    ticket = mfa_ticket.issue(1, "h", now=NOW)
    _, signature = ticket.split(".")
    forged = forge({"u": 1, "e": int(NOW) + 10**9, "p": mfa_ticket.fingerprint("h")}, signature)

    assert mfa_ticket.read(forged, now=NOW) is None


def test_a_flipped_character_in_the_signature_is_caught() -> None:
    ticket = mfa_ticket.issue(1, "h", now=NOW)
    body, signature = ticket.split(".")
    flipped = signature[:-1] + ("A" if signature[-1] != "A" else "B")

    assert mfa_ticket.read(f"{body}.{flipped}", now=NOW) is None


def test_a_ticket_from_another_deployment_secret_is_refused(monkeypatch) -> None:
    ticket = mfa_ticket.issue(1, "h", now=NOW)
    monkeypatch.setattr(
        mfa_ticket, "get_settings", lambda: SimpleNamespace(secret_key="a-different-secret")
    )

    assert mfa_ticket.read(ticket, now=NOW) is None


def test_a_validly_signed_but_malformed_payload_is_refused(monkeypatch) -> None:
    body = base64.urlsafe_b64encode(json.dumps({"u": "x", "e": "y"}).encode()).decode().rstrip("=")
    signed = f"{body}.{mfa_ticket._sign(body)}"

    assert mfa_ticket.read(signed, now=NOW) is None
    missing = base64.urlsafe_b64encode(json.dumps({"u": 1}).encode()).decode().rstrip("=")
    assert mfa_ticket.read(f"{missing}.{mfa_ticket._sign(missing)}", now=NOW) is None


def test_an_over_long_ticket_is_refused_even_with_a_genuine_signature() -> None:
    # Properly signed and otherwise valid, but padded: no real ticket is this long,
    # so it is turned away before any work is spent on it.
    payload = {"u": 1, "e": int(NOW) + 300, "p": mfa_ticket.fingerprint("h"), "pad": "x" * 400}
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    ticket = f"{body}.{mfa_ticket._sign(body)}"

    assert len(ticket) > mfa_ticket._MAX_LENGTH
    assert mfa_ticket.read(ticket, now=NOW) is None


def test_a_ticket_just_inside_the_limit_is_still_read() -> None:
    ticket = mfa_ticket.issue(123456789, "h", now=NOW)

    assert len(ticket) <= mfa_ticket._MAX_LENGTH
    assert mfa_ticket.read(ticket, now=NOW) is not None
