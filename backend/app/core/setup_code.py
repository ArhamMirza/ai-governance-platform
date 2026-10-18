"""The code that guards creating the very first account.

Registration is open only while no account exists. On a development machine
that is fine. On a real deployment, though, whoever reaches the new server
first would become its administrator, so the first account needs a code that
only the person starting the server can see: printed in the server's log at
startup, or set in advance as SETUP_CODE.
"""

import hmac
import logging
import secrets

from sqlalchemy.orm import Session

from app.core.config import get_settings

logger = logging.getLogger("uvicorn.error")

_generated: str | None = None


def required() -> bool:
    return get_settings().is_real_deployment


def expected() -> str:
    """The code in force: the configured one, else one made once per run."""
    global _generated
    configured = (get_settings().setup_code or "").strip()
    if configured:
        return configured
    if _generated is None:
        _generated = secrets.token_urlsafe(12)
    return _generated


def matches(candidate: str | None) -> bool:
    if not candidate:
        return False
    return hmac.compare_digest(candidate.strip().encode(), expected().encode())


def announce(db: Session) -> None:
    """At startup: tell the operator the code, if an account is still to be made.

    The code is printed only when the server made it up. A configured one is
    the operator's own and is not echoed into the log.
    """
    if not required():
        return
    from app.services import auth_service

    if not auth_service.registration_open(db):
        return
    if (get_settings().setup_code or "").strip():
        logger.warning("No account exists yet. Creating the first one needs your SETUP_CODE.")
    else:
        logger.warning(
            "No account exists yet. To create the first one, enter this setup code: %s",
            expected(),
        )
