"""Symmetric encryption for secrets the app has to store and use again.

An AI provider's API key can't be hashed the way a password is -- the app
needs the original to make a call -- so it's encrypted at rest instead, with
a key derived from the deployment's own ``secret_key``. That means rotating
``secret_key`` makes what was stored unreadable: provider keys have to be
re-entered, and people with two-step sign-in must use a recovery code (or be
reset by an administrator), because their authenticator secret can no longer
be decrypted.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _fernet() -> Fernet:
    # Fernet wants 32 url-safe base64 bytes; the deployment secret is an
    # arbitrary string, so it's hashed to exactly that shape.
    digest = hashlib.sha256(get_settings().secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str | None:
    """The stored secret, or None if it can't be read back.

    A key encrypted under a previous ``secret_key`` fails here rather than
    raising: the caller treats it as "no key configured" and asks for it
    again, which is the recoverable outcome.
    """
    try:
        return _fernet().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError):
        return None
