"""Time-based one-time passwords (RFC 6238), the codes an authenticator app shows.

Standard library only. HMAC-SHA1 with six digits and 30-second steps is what
Google Authenticator, Microsoft Authenticator, Authy and 1Password all
implement, so it is the one profile that works with all of them.
"""

import base64
import hashlib
import hmac
import secrets
import struct
from urllib.parse import quote, urlencode

STEP_SECONDS = 30
DIGITS = 6
# A code from one step either side of now is accepted, for a phone whose clock
# is a little off. Wider would make a stolen or guessed code live longer.
DRIFT_STEPS = 1
ISSUER = "AI Governance Platform"


def new_secret() -> str:
    """20 random bytes (160 bits, the size RFC 4226 recommends), as the unpadded
    base32 text authenticator apps expect."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _decode(secret: str) -> bytes:
    cleaned = secret.replace(" ", "").upper()
    return base64.b32decode(cleaned + "=" * (-len(cleaned) % 8))


def step_at(timestamp: float) -> int:
    return int(timestamp // STEP_SECONDS)


def code_for_step(secret: str, step: int) -> str:
    digest = hmac.new(_decode(secret), struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10**DIGITS).zfill(DIGITS)


def verify(secret: str, code: str, *, now: float, after_step: int | None = None) -> int | None:
    """The step the code belongs to, or None if it isn't a valid current code.

    `after_step` is the last step already used for this account: a code from
    that step or earlier is refused, so a code seen once -- over a shoulder, in
    a phishing page -- cannot be used a second time.
    """
    cleaned = code.replace(" ", "").replace("-", "")
    if len(cleaned) != DIGITS or not cleaned.isascii() or not cleaned.isdigit():
        return None
    current = step_at(now)
    for step in range(current - DRIFT_STEPS, current + DRIFT_STEPS + 1):
        if after_step is not None and step <= after_step:
            continue
        if hmac.compare_digest(code_for_step(secret, step), cleaned):
            return step
    return None


def provisioning_uri(secret: str, account: str) -> str:
    """The `otpauth://` link an authenticator app reads from the QR code."""
    label = f"{quote(ISSUER)}:{quote(account)}"
    query = urlencode(
        {
            "secret": secret,
            "issuer": ISSUER,
            "algorithm": "SHA1",
            "digits": DIGITS,
            "period": STEP_SECONDS,
        },
        quote_via=quote,
    )
    return f"otpauth://totp/{label}?{query}"
