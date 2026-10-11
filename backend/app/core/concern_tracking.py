"""Tracking codes and triage timing for concerns -- ISO/IEC 42001 A.3.3.
Pure functions, computed live, never stored.

A tracking code is how someone who reported anonymously comes back to see
what happened: the code is the only thing that links them to the concern, so
it's long enough that guessing one isn't practical, and only its hash is
kept -- reading the table doesn't reveal a code.
"""

import hashlib
import secrets
from datetime import date, timedelta

# No 0/O, 1/I/L: a code read off a screen and typed back shouldn't hinge on
# telling them apart. 32 symbols x 12 characters = 60 bits.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 12
_GROUP = 4


def new_tracking_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def format_code(code: str) -> str:
    """ABCDEFGHJKMN -> ABCD-EFGH-JKMN, easier to read and copy."""
    return "-".join(code[i : i + _GROUP] for i in range(0, len(code), _GROUP))


def normalise_code(text: str) -> str:
    """What someone typed back, however they spaced or cased it."""
    return "".join(ch for ch in text.upper() if ch in ALPHABET)


def hash_code(code: str) -> str:
    return hashlib.sha256(normalise_code(code).encode()).hexdigest()


def looks_like_a_code(text: str) -> bool:
    return len(normalise_code(text)) == CODE_LENGTH


def acknowledge_by(received_on: date, acknowledge_within_days: int) -> date:
    return received_on + timedelta(days=acknowledge_within_days)


def awaiting_triage(
    status: str, received_on: date, acknowledge_within_days: int, today: date
) -> bool:
    """Still unacknowledged past the limit. The last day of the window itself
    isn't late."""
    return status == "received" and today > acknowledge_by(received_on, acknowledge_within_days)
