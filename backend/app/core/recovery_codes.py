"""Single-use codes for signing in when the authenticator app isn't to hand.

Ten are made when two-step sign-in is switched on, shown once, and kept only
as hashes. Each works once. They are 50 bits of randomness in groups of five
characters, which is out of reach of guessing while sign-in attempts are
limited, so a plain SHA-256 (rather than a slow password hash) is enough.
"""

import hashlib
import secrets

COUNT = 10
# No 0/O, 1/I/L: a code read off a printout must not be ambiguous.
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_GROUP = 5
_GROUPS = 2
LENGTH = _GROUP * _GROUPS


def generate() -> list[str]:
    codes = []
    for _ in range(COUNT):
        raw = "".join(secrets.choice(_ALPHABET) for _ in range(LENGTH))
        codes.append("-".join(raw[i : i + _GROUP] for i in range(0, LENGTH, _GROUP)))
    return codes


def normalize(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def looks_like_one(code: str) -> bool:
    cleaned = normalize(code)
    return len(cleaned) == LENGTH and all(ch in _ALPHABET for ch in cleaned)


def hash_code(code: str) -> str:
    return hashlib.sha256(normalize(code).encode()).hexdigest()
