"""Password hashing and session tokens.

Deliberately stdlib-only (hashlib + secrets) rather than adding a dependency
like passlib/bcrypt -- PBKDF2-HMAC-SHA256 is a NIST-approved KDF and the
`hashlib` implementation is C-accelerated, which is what actually matters for
brute-force resistance.
"""

import hashlib
import hmac
import secrets

PBKDF2_ITERATIONS = 600_000
_ALGORITHM = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return f"{_ALGORITHM}${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt, expected_hex = password_hash.split("$")
    except ValueError:
        return False
    if algorithm != _ALGORITHM:
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), int(iterations_str)
    )
    return hmac.compare_digest(digest.hex(), expected_hex)


def generate_session_token() -> str:
    """The value that goes in the cookie -- never stored anywhere."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """The value stored in the sessions table. A straight SHA-256 (no salt)
    is fine here: the input is already 32 bytes of CSPRNG output, so it
    carries no guessable structure for a rainbow table to exploit."""
    return hashlib.sha256(token.encode()).hexdigest()
