"""Two-step sign-in: setting up an authenticator app, checking its codes, the
recovery codes, and the organization rule that administrators must use it.

The second step of signing in (the ticket and the session) lives in
auth_service; this module is everything about the factor itself. It does not
import auth_service, so auth_service can use it.
"""

import time
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core import recovery_codes, totp
from app.core.attempt_limiter import AttemptLimiter
from app.core.crypto import decrypt, encrypt
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError, ValidationError
from app.core.security import hash_session_token, verify_password
from app.models.mfa import SecuritySettings, UserMFA
from app.models.user import User, UserRole
from app.repositories import mfa_repository, session_repository, user_repository
from app.schemas.mfa import SecuritySettingsRead
from app.services import audit_service

ENTITY_TYPE = "User"
SETTINGS_ENTITY_TYPE = "SecuritySettings"
_WINDOW = timedelta(minutes=15)
MAX_WRONG_CODES = 5

# Per account, and not cleared by a correct password: someone who knows the
# password still gets only five guesses at the code, however often they
# re-enter it. Only a correct code clears it.
_wrong_codes = AttemptLimiter(
    max_failures=MAX_WRONG_CODES,
    window=_WINDOW,
    message="Too many incorrect codes. Try again in 15 minutes.",
)


def reset_rate_limits() -> None:
    _wrong_codes.reset()


def _audit(db: Session, user_id: int, action: str, actor_id: int | None, diff: dict | None = None):
    audit_service.log(db, ENTITY_TYPE, user_id, action, actor_id, diff)


# ---------- the organization rule ----------


def get_settings(db: Session) -> SecuritySettings:
    settings = mfa_repository.get_settings(db)
    if settings is None:
        settings = mfa_repository.save_settings(db, SecuritySettings(require_mfa_for_admins=False))
    return settings


def required_for_admins(db: Session) -> bool:
    """Read without writing a row, since it is asked on every admin request."""
    settings = mfa_repository.get_settings(db)
    return bool(settings and settings.require_mfa_for_admins)


def setup_required(db: Session, user: User) -> bool:
    """An administrator without two-step sign-in, while the organization requires it."""
    return user.role == UserRole.ADMIN and not user.mfa_enabled and required_for_admins(db)


def read_settings(db: Session) -> SecuritySettingsRead:
    return SecuritySettingsRead(
        require_mfa_for_admins=required_for_admins(db),
        admins_without_mfa=mfa_repository.count_admins_without_mfa(db),
    )


def update_settings(db: Session, require_for_admins: bool, actor: User) -> SecuritySettingsRead:
    if require_for_admins and not actor.mfa_enabled:
        raise ConflictError(
            "Turn on two-step sign-in for your own account first, so this can't lock you out."
        )
    settings = get_settings(db)
    changed = settings.require_mfa_for_admins != require_for_admins
    settings.require_mfa_for_admins = require_for_admins
    mfa_repository.save_settings(db, settings)
    if changed:
        audit_service.log(
            db,
            SETTINGS_ENTITY_TYPE,
            settings.id,
            "updated",
            actor.id,
            {"require_mfa_for_admins": require_for_admins},
        )
    return read_settings(db)


# ---------- a person's own authenticator ----------


def remaining_recovery_codes(db: Session, user: User) -> int:
    return mfa_repository.unused_recovery_codes(db, user.id) if user.mfa_enabled else 0


def begin_setup(db: Session, user: User) -> tuple[str, str]:
    """A new secret and the link for the QR code. Replaces an earlier,
    unfinished set-up; does nothing to sign-in until it is confirmed."""
    if user.mfa_enabled:
        raise ConflictError("Two-step sign-in is already on. Turn it off first to set it up again.")
    secret = totp.new_secret()
    mfa = user.mfa or UserMFA(user_id=user.id, secret_encrypted="")
    mfa.secret_encrypted = encrypt(secret)
    mfa.confirmed = False
    mfa.last_used_step = None
    mfa_repository.save(db, mfa)
    db.refresh(user)
    return secret, totp.provisioning_uri(secret, user.email)


def confirm_setup(db: Session, user: User, code: str, *, now: float | None = None) -> list[str]:
    """Turns two-step sign-in on once the person has shown their app works,
    and returns the recovery codes -- the only time they are readable."""
    mfa = user.mfa
    if mfa is None or mfa.confirmed:
        raise ValidationError("Start the set-up first.")
    _wrong_codes.check(str(user.id))
    secret = decrypt(mfa.secret_encrypted)
    if secret is None:
        raise ValidationError("This set-up can't be read any more. Start it again.")
    step = totp.verify(secret, code, now=_now(now))
    if step is None:
        _wrong_codes.record_failure(str(user.id))
        raise ValidationError(
            "That code isn't right. Check that the time on your phone is correct, then try "
            "the next code it shows."
        )
    _wrong_codes.reset(str(user.id))
    mfa.confirmed = True
    mfa.last_used_step = step
    mfa.confirmed_at = datetime.now(UTC)
    mfa_repository.save(db, mfa)
    codes = recovery_codes.generate()
    mfa_repository.replace_recovery_codes(db, user.id, [recovery_codes.hash_code(c) for c in codes])
    _audit(db, user.id, "mfa_enabled", user.id)
    db.refresh(user)
    return codes


def _check_second_factor(
    db: Session, user: User, code: str, now: float | None = None
) -> str | None:
    """ "totp" or "recovery" if the code is good (and is now spent), else None.

    If the stored secret can't be read (the deployment secret was rotated) no
    code is accepted: it fails closed, and an administrator has to reset the
    person's two-step sign-in."""
    mfa = user.mfa
    if mfa is None or not mfa.confirmed:
        return None
    if recovery_codes.looks_like_one(code):
        spent = mfa_repository.use_recovery_code(db, user.id, recovery_codes.hash_code(code))
        return "recovery" if spent else None
    secret = decrypt(mfa.secret_encrypted)
    if secret is None:
        return None
    step = totp.verify(secret, code, now=_now(now), after_step=mfa.last_used_step)
    if step is None:
        return None
    return "totp" if mfa_repository.advance_step(db, mfa.id, step) else None


def verify_for_login(
    db: Session, user: User, code: str, ip: str | None, *, now: float | None = None
) -> str:
    """The second step of signing in. Raises if the code is wrong; five wrong
    codes in 15 minutes lock the account's codes for the rest of the window."""
    key = str(user.id)
    _wrong_codes.check(key)
    method = _check_second_factor(db, user, code, now)
    if method is None:
        _wrong_codes.record_failure(key)
        _audit(db, user.id, "mfa_failed", None, {"ip": ip})
        if _wrong_codes.failure_count(key) >= MAX_WRONG_CODES:
            _audit(db, user.id, "mfa_locked", None, {"ip": ip, "minutes": 15})
        raise AuthenticationError("That code isn't right.")
    _wrong_codes.reset(key)
    if method == "recovery":
        _audit(
            db,
            user.id,
            "mfa_recovery_used",
            user.id,
            {"ip": ip, "remaining": mfa_repository.unused_recovery_codes(db, user.id)},
        )
    return method


def _prove_it_is_them(db: Session, user: User, password: str, code: str, now: float | None) -> None:
    """For turning it off or making new recovery codes: the password and a
    current code, so someone at an unlocked laptop can't do it."""
    key = str(user.id)
    _wrong_codes.check(key)
    if not verify_password(password, user.password_hash):
        _wrong_codes.record_failure(key)
        raise AuthenticationError("Your password is incorrect.")
    if _check_second_factor(db, user, code, now) is None:
        _wrong_codes.record_failure(key)
        raise AuthenticationError("That code isn't right.")
    _wrong_codes.reset(key)


def disable(
    db: Session,
    user: User,
    password: str,
    code: str,
    keep_token: str | None,
    *,
    now: float | None = None,
) -> None:
    if not user.mfa_enabled:
        raise ConflictError("Two-step sign-in isn't on.")
    if user.role == UserRole.ADMIN and required_for_admins(db):
        raise ConflictError("Your organization requires two-step sign-in for administrators.")
    _prove_it_is_them(db, user, password, code, now)
    mfa_repository.delete_for_user(db, user.id)
    _end_sessions(db, user.id, keep_token)
    _audit(db, user.id, "mfa_disabled", user.id)


def regenerate_recovery_codes(
    db: Session, user: User, password: str, code: str, *, now: float | None = None
) -> list[str]:
    if not user.mfa_enabled:
        raise ConflictError("Two-step sign-in isn't on.")
    _prove_it_is_them(db, user, password, code, now)
    codes = recovery_codes.generate()
    mfa_repository.replace_recovery_codes(db, user.id, [recovery_codes.hash_code(c) for c in codes])
    _audit(db, user.id, "mfa_recovery_codes_replaced", user.id)
    return codes


def admin_reset(db: Session, user_id: int, actor_id: int) -> User:
    """For someone who has lost their phone and their recovery codes: switches
    their two-step sign-in off and signs them out everywhere. Never your own --
    that would let a stolen password and session undo the protection."""
    if user_id == actor_id:
        raise ConflictError("Ask another administrator to reset your two-step sign-in.")
    user = user_repository.get(db, user_id)
    if user is None:
        raise NotFoundError("User", user_id)
    had_it = user.mfa_enabled
    mfa_repository.delete_for_user(db, user.id)
    _end_sessions(db, user.id, None)
    _wrong_codes.reset(str(user.id))
    _audit(db, user.id, "mfa_reset", actor_id, {"was_on": had_it})
    db.refresh(user)
    return user


def _end_sessions(db: Session, user_id: int, keep_token: str | None) -> None:
    keep = hash_session_token(keep_token) if keep_token else None
    session_repository.delete_for_user(db, user_id, keep)


def _now(now: float | None) -> float:
    return time.time() if now is None else now
