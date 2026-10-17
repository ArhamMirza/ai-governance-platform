"""The enrollment key the browser extension presents to this server.

One key for the whole organization, pushed to managed browsers by IT. It is a
shared secret rather than a per-person credential, so what it guards is
limited on purpose: the extension may read the policy and send usage counts,
nothing else. Only its hash is stored -- reading the table doesn't reveal the
key -- and it is shown once, when it is made.
"""

import hashlib
import hmac
import secrets

PREFIX = "aigk_"


def new_enrollment_key() -> str:
    return PREFIX + secrets.token_urlsafe(32)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.strip().encode()).hexdigest()


def key_matches(presented: str, stored_hash: str | None) -> bool:
    """Constant-time, so how long the check takes says nothing about how much
    of a guess was right."""
    if not stored_hash:
        return False
    return hmac.compare_digest(hash_key(presented), stored_hash)


def hint(key: str) -> str:
    """The last four characters, to tell one key from another without keeping it."""
    return key[-4:]
