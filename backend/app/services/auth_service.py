"""Signing in, sessions, and changing a password.

Registration is a one-time bootstrap -- open only while no user exists yet;
every other account is created by an administrator (user_service). Sign-in,
sign-out, password changes and lockouts are written to the audit log against
the person's account, so "who signed in, from where, and who was refused" can
be answered afterwards.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session as DbSession

from app.core import mfa_ticket, password_policy, setup_code
from app.core.attempt_limiter import AttemptLimiter
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
from app.repositories import password_history_repository, session_repository, user_repository
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest
from app.schemas.mfa import MfaLogin
from app.services import audit_service, mfa_service

ENTITY_TYPE = "User"
SESSION_LIFETIME = timedelta(days=14)

# The password in use and the four before it can't be chosen again.
PASSWORD_HISTORY_DEPTH = 5

# Failed-login lockout. In-memory and per-process, which is fine for this
# app's single-process, single-tenant deployment model (like the rest of
# its state, it resets on restart) -- the point is to make a public login
# form an unattractive brute-force target, not to survive a restart.
_FAILED_LOGIN_WINDOW = timedelta(minutes=15)
_MAX_FAILED_LOGINS = 5
_MAX_TRACKED_EMAILS = 10_000

_failed_logins: dict[str, list[datetime]] = {}

# Per address, on top of the per-account lock above: one machine trying many
# accounts is slowed even though no single account reaches its limit. Behind a
# reverse proxy every request appears to come from the proxy, so a deployment
# there should forward the real client address (uvicorn --proxy-headers).
_login_attempts_by_address = AttemptLimiter(
    max_failures=20,
    window=_FAILED_LOGIN_WINDOW,
    message="Too many failed sign-in attempts from this address. Try again in 15 minutes.",
)

# Someone holding a stolen session can't use "change password" to guess the
# real password: wrong current passwords are counted per account.
_setup_code_attempts = AttemptLimiter(
    max_failures=5,
    window=_FAILED_LOGIN_WINDOW,
    message="Too many incorrect setup codes. Try again in 15 minutes.",
)

_password_change_attempts = AttemptLimiter(
    max_failures=5,
    window=_FAILED_LOGIN_WINDOW,
    message="Too many incorrect passwords. Try again in 15 minutes.",
)


def reset_rate_limits() -> None:
    """For tests: every limiter here is process-wide state."""
    _failed_logins.clear()
    _login_attempts_by_address.reset()
    _password_change_attempts.reset()
    _setup_code_attempts.reset()
    mfa_service.reset_rate_limits()


def _recent_failures(email: str, now: datetime) -> list[datetime]:
    attempts = [t for t in _failed_logins.get(email, []) if now - t < _FAILED_LOGIN_WINDOW]
    _failed_logins[email] = attempts
    return attempts


def _record_failure(email: str, now: datetime) -> int:
    if len(_failed_logins) >= _MAX_TRACKED_EMAILS and email not in _failed_logins:
        _failed_logins.clear()
    attempts = _failed_logins.setdefault(email, [])
    attempts.append(now)
    return len(attempts)


def _utc_now_naive() -> datetime:
    # SQLite drops tzinfo on read back (confirmed: a DateTime(timezone=True)
    # column round-trips as a naive datetime), so expires_at comparisons must
    # use a naive "now" consistently or they raise on offset-naive vs
    # offset-aware comparison.
    return datetime.now(UTC).replace(tzinfo=None)


def _audit(
    db: DbSession, user_id: int, action: str, actor_id: int | None, diff: dict | None = None
) -> None:
    audit_service.log(db, ENTITY_TYPE, user_id, action, actor_id, diff)


def registration_open(db: DbSession) -> bool:
    return user_repository.count(db) == 0


def register(db: DbSession, data: RegisterRequest, ip: str | None = None) -> User:
    if not registration_open(db):
        raise ConflictError("Registration is closed; an account already exists.")
    if setup_code.required():
        key = ip or "unknown"
        _setup_code_attempts.check(key)
        if not setup_code.matches(data.setup_code):
            _setup_code_attempts.record_failure(key)
            raise ValidationError(
                "The setup code is missing or wrong. It is printed in the server's log when "
                "it starts, or it is the SETUP_CODE you configured."
            )
    if "@" not in data.email:
        raise ValidationError("Enter a valid email address.")
    email = data.email.strip().lower()
    password_policy.require(data.password, email=email, name=data.name)

    user = User(
        name=data.name,
        email=email,
        password_hash=hash_password(data.password),
        password_changed_at=datetime.now(UTC),
    )
    return user_repository.create(db, user)


def authenticate(db: DbSession, data: LoginRequest, ip: str | None = None) -> User:
    email = data.email.strip().lower()
    now = _utc_now_naive()
    if ip is not None:
        _login_attempts_by_address.check(ip)
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
        failures = _record_failure(email, now)
        if ip is not None:
            _login_attempts_by_address.record_failure(ip)
        if user is not None:
            _audit(db, user.id, "login_failed", None, {"ip": ip})
            if failures >= _MAX_FAILED_LOGINS:
                _audit(db, user.id, "account_locked", None, {"ip": ip, "minutes": 15})
        raise AuthenticationError("Incorrect email or password.")
    if not user.is_active:
        raise AuthenticationError("This account has been deactivated.")

    _failed_logins.pop(email, None)
    session_repository.delete_expired(db, now)
    # Accounts from before the current rules (or with a password an admin
    # chose) are asked to choose a new one; the plain text is only ever
    # available here, at the moment it is typed.
    if not user.must_change_password and password_policy.problem_with(
        data.password, email=user.email, name=user.name
    ):
        user.must_change_password = True
        user = user_repository.save(db, user)
    return user


def record_login(
    db: DbSession, user: User, ip: str | None, second_factor: str | None = None
) -> None:
    """Written once the person is actually in: after the password, and after
    the code too when the account has two-step sign-in."""
    diff: dict = {"ip": ip}
    if second_factor is not None:
        diff["second_factor"] = second_factor
    _audit(db, user.id, "login", user.id, diff)


_SIGN_IN_EXPIRED = "Your sign-in took too long or is no longer valid. Enter your password again."


def complete_two_step(db: DbSession, data: MfaLogin, ip: str | None) -> tuple[User, str]:
    """The second step: the ticket from a correct password, and a code. Returns
    the person and which kind of code was used."""
    if ip is not None:
        _login_attempts_by_address.check(ip)
    ticket = mfa_ticket.read(data.ticket)
    user = user_repository.get(db, ticket.user_id) if ticket is not None else None
    if (
        ticket is None
        or user is None
        or not user.is_active
        or not user.mfa_enabled
        or mfa_ticket.fingerprint(user.password_hash) != ticket.password_fingerprint
    ):
        raise AuthenticationError(_SIGN_IN_EXPIRED)
    try:
        method = mfa_service.verify_for_login(db, user, data.code, ip)
    except AuthenticationError:
        if ip is not None:
            _login_attempts_by_address.record_failure(ip)
        raise
    session_repository.delete_expired(db, _utc_now_naive())
    return user, method


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
    if not token:
        return
    user = get_user_for_token(db, token)
    session_repository.delete_by_token_hash(db, hash_session_token(token))
    if user is not None:
        _audit(db, user.id, "logout", user.id)


def end_sessions(db: DbSession, user_id: int, keep_token: str | None = None) -> int:
    """Signs a user out of every device, optionally sparing the one asking.
    Called whenever what a session was allowed to do has changed: a password
    change or reset, a new role, deactivation."""
    keep = hash_session_token(keep_token) if keep_token else None
    return session_repository.delete_for_user(db, user_id, keep)


def sign_out_everywhere(db: DbSession, user: User, keep_token: str | None) -> int:
    """Ends every other session of the signed-in person."""
    ended = end_sessions(db, user.id, keep_token)
    _audit(db, user.id, "sessions_ended", user.id, {"count": ended})
    return ended


def replace_password(db: DbSession, user: User, new_password: str, *, must_change: bool) -> User:
    """Sets a new password, remembering the old one so it can't come back.
    The caller has already checked the new one against the rules."""
    password_history_repository.remember(
        db, user.id, user.password_hash, keep=PASSWORD_HISTORY_DEPTH - 1
    )
    user.password_hash = hash_password(new_password)
    user.must_change_password = must_change
    user.password_changed_at = datetime.now(UTC)
    return user_repository.save(db, user)


def change_password(
    db: DbSession, user: User, data: ChangePasswordRequest, keep_token: str | None
) -> User:
    key = str(user.id)
    _password_change_attempts.check(key)
    if not verify_password(data.current_password, user.password_hash):
        _password_change_attempts.record_failure(key)
        raise AuthenticationError("Your current password is incorrect.")

    password_policy.require(data.new_password, email=user.email, name=user.name)
    previous = [user.password_hash, *password_history_repository.recent_hashes(db, user.id)]
    if any(verify_password(data.new_password, old) for old in previous):
        raise ValidationError(
            "You've used that password recently. Choose one you haven't used before."
        )

    _password_change_attempts.reset(key)
    user = replace_password(db, user, data.new_password, must_change=False)
    ended = end_sessions(db, user.id, keep_token)
    _audit(db, user.id, "password_changed", user.id, {"other_sessions_ended": ended})
    return user
