"""Single-user local auth: one self-registered account, session-cookie login.

Registration is a one-time bootstrap -- open only while no user exists yet.
There is no invite flow and no password reset in this MVP; if the one
account's password is lost, an operator resets it at the database level.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session as DbSession

from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    RateLimitedError,
    ValidationError,
)
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.models.session import Session as UserSession
from app.models.user import User
from app.repositories import session_repository, user_repository
from app.schemas.auth import LoginRequest, RegisterRequest

SESSION_LIFETIME = timedelta(days=14)

# Failed-login lockout. In-memory and per-process, which is fine for this
# app's single-process, single-tenant deployment model (like the rest of
# its state, it resets on restart) -- the point is to make a public login
# form an unattractive brute-force target, not to survive a restart.
_FAILED_LOGIN_WINDOW = timedelta(minutes=15)
_MAX_FAILED_LOGINS = 5
_MAX_TRACKED_EMAILS = 10_000

_failed_logins: dict[str, list[datetime]] = {}


def _recent_failures(email: str, now: datetime) -> list[datetime]:
    attempts = [t for t in _failed_logins.get(email, []) if now - t < _FAILED_LOGIN_WINDOW]
    _failed_logins[email] = attempts
    return attempts


def _record_failure(email: str, now: datetime) -> None:
    if len(_failed_logins) >= _MAX_TRACKED_EMAILS and email not in _failed_logins:
        _failed_logins.clear()
    _failed_logins.setdefault(email, []).append(now)


def _utc_now_naive() -> datetime:
    # SQLite drops tzinfo on read back (confirmed: a DateTime(timezone=True)
    # column round-trips as a naive datetime), so expires_at comparisons must
    # use a naive "now" consistently or they raise on offset-naive vs
    # offset-aware comparison.
    return datetime.now(UTC).replace(tzinfo=None)


def registration_open(db: DbSession) -> bool:
    return user_repository.count(db) == 0


def register(db: DbSession, data: RegisterRequest) -> User:
    if not registration_open(db):
        raise ConflictError("Registration is closed; an account already exists.")
    if "@" not in data.email:
        raise ValidationError("Enter a valid email address.")

    user = User(
        name=data.name,
        email=data.email.strip().lower(),
        password_hash=hash_password(data.password),
    )
    return user_repository.create(db, user)


def authenticate(db: DbSession, data: LoginRequest) -> User:
    email = data.email.strip().lower()
    now = _utc_now_naive()
    if len(_recent_failures(email, now)) >= _MAX_FAILED_LOGINS:
        raise RateLimitedError(
            "Too many failed login attempts for this account. Try again in 15 minutes."
        )

    user = user_repository.get_by_email(db, email)
    # Verify against a real hash even on a missing user, so the response
    # time doesn't leak whether the email is registered.
    password_hash = user.password_hash if user is not None else hash_password("")
    valid = verify_password(data.password, password_hash)
    if user is None or not valid:
        _record_failure(email, now)
        raise AuthenticationError("Incorrect email or password.")
    if not user.is_active:
        raise AuthenticationError("This account has been deactivated.")
    _failed_logins.pop(email, None)
    return user


def create_session(db: DbSession, user: User) -> str:
    token = generate_session_token()
    session_repository.create(
        db,
        UserSession(
            token_hash=hash_session_token(token),
            user_id=user.id,
            expires_at=_utc_now_naive() + SESSION_LIFETIME,
        ),
    )
    return token


def get_user_for_token(db: DbSession, token: str | None) -> User | None:
    if not token:
        return None
    session = session_repository.get_by_token_hash(db, hash_session_token(token))
    if session is None:
        return None
    if session.expires_at < _utc_now_naive():
        session_repository.delete(db, session)
        return None
    return user_repository.get(db, session.user_id)


def revoke_session(db: DbSession, token: str | None) -> None:
    if token:
        session_repository.delete_by_token_hash(db, hash_session_token(token))
