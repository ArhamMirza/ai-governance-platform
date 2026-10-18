from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core import mfa_ticket, setup_code
from app.core.config import get_settings
from app.core.database import get_db
from app.dependencies import get_session_user, session_cookie_name
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    RegistrationStatus,
    SessionsEnded,
    UserRead,
)
from app.schemas.mfa import (
    MfaChallenge,
    MfaCode,
    MfaLogin,
    MfaProof,
    MfaSetup,
    MfaStatus,
    RecoveryCodes,
)
from app.services import auth_service, mfa_service

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_MAX_AGE_SECONDS = int(auth_service.SESSION_LIFETIME.total_seconds())


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=session_cookie_name(),
        value=token,
        max_age=COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        # Strict: the cookie is never sent on a request that starts on another
        # site. The app and its API are the same site, so nothing legitimate
        # is affected.
        samesite="strict",
        secure=settings.cookie_secure,
    )


def _view(db: Session, user: User) -> UserRead:
    """The user as the app sees them, with whether they must still set up
    two-step sign-in (which depends on the organization's setting)."""
    view = UserRead.model_validate(user)
    view.mfa_setup_required = mfa_service.setup_required(db, user)
    return view


def _client_address(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/registration-status", response_model=RegistrationStatus)
def registration_status(db: Session = Depends(get_db)) -> RegistrationStatus:
    is_open = auth_service.registration_open(db)
    return RegistrationStatus(
        registration_open=is_open, setup_code_required=is_open and setup_code.required()
    )


@router.post("/register", response_model=UserRead, status_code=201)
def register(
    data: RegisterRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> UserRead:
    user = auth_service.register(db, data, _client_address(request))
    token = auth_service.create_session(db, user)
    _set_session_cookie(response, token)
    return _view(db, user)


@router.post("/login", response_model=UserRead | MfaChallenge)
def login(
    data: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> UserRead | MfaChallenge:
    """A correct password signs in -- unless the account has two-step sign-in,
    in which case there is no session yet, only a ticket to send with a code
    to /login/two-step."""
    ip = _client_address(request)
    user = auth_service.authenticate(db, data, ip)
    if user.mfa_enabled:
        return MfaChallenge(ticket=mfa_ticket.issue(user.id, user.password_hash))
    token = auth_service.create_session(db, user)
    _set_session_cookie(response, token)
    auth_service.record_login(db, user, ip)
    return _view(db, user)


@router.post("/login/two-step", response_model=UserRead)
def login_two_step(
    data: MfaLogin, request: Request, response: Response, db: Session = Depends(get_db)
) -> UserRead:
    ip = _client_address(request)
    user, method = auth_service.complete_two_step(db, data, ip)
    token = auth_service.create_session(db, user)
    _set_session_cookie(response, token)
    auth_service.record_login(db, user, ip, second_factor=method)
    return _view(db, user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    token = request.cookies.get(session_cookie_name())
    auth_service.revoke_session(db, token)
    response.delete_cookie(
        session_cookie_name(),
        secure=get_settings().cookie_secure,
        httponly=True,
        samesite="strict",
    )


# These use get_session_user, not get_current_user: they are the routes
# someone who must still choose a new password is allowed to reach.
@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_session_user), db: Session = Depends(get_db)) -> UserRead:
    return _view(db, user)


@router.post("/change-password", response_model=UserRead)
def change_password(
    data: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_session_user),
) -> UserRead:
    """Needs the current password, and signs every other device out."""
    changed = auth_service.change_password(
        db, user, data, keep_token=request.cookies.get(session_cookie_name())
    )
    return _view(db, changed)


@router.post("/sign-out-everywhere", response_model=SessionsEnded)
def sign_out_everywhere(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_session_user),
) -> SessionsEnded:
    ended = auth_service.sign_out_everywhere(
        db, user, keep_token=request.cookies.get(session_cookie_name())
    )
    return SessionsEnded(other_sessions_ended=ended)


# ---------- your own two-step sign-in ----------
# All of these use get_session_user: an administrator the organization requires
# to set it up has to be able to reach them before anything else.


@router.get("/two-step", response_model=MfaStatus)
def two_step_status(
    db: Session = Depends(get_db), user: User = Depends(get_session_user)
) -> MfaStatus:
    return MfaStatus(
        enabled=user.mfa_enabled,
        recovery_codes_remaining=mfa_service.remaining_recovery_codes(db, user),
        setup_required=mfa_service.setup_required(db, user),
    )


@router.post("/two-step/setup", response_model=MfaSetup)
def two_step_setup(
    db: Session = Depends(get_db), user: User = Depends(get_session_user)
) -> MfaSetup:
    """Starts setting up an authenticator app. Does nothing to sign-in until
    /two-step/confirm is given a working code."""
    secret, uri = mfa_service.begin_setup(db, user)
    return MfaSetup(secret=secret, otpauth_uri=uri)


@router.post("/two-step/confirm", response_model=RecoveryCodes)
def two_step_confirm(
    data: MfaCode, db: Session = Depends(get_db), user: User = Depends(get_session_user)
) -> RecoveryCodes:
    """Turns it on, and returns the recovery codes -- the only time they are shown."""
    return RecoveryCodes(recovery_codes=mfa_service.confirm_setup(db, user, data.code))


@router.post("/two-step/disable", status_code=204)
def two_step_disable(
    data: MfaProof,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_session_user),
) -> None:
    mfa_service.disable(
        db, user, data.password, data.code, keep_token=request.cookies.get(session_cookie_name())
    )


@router.post("/two-step/recovery-codes", response_model=RecoveryCodes)
def two_step_new_recovery_codes(
    data: MfaProof, db: Session = Depends(get_db), user: User = Depends(get_session_user)
) -> RecoveryCodes:
    """Replaces all recovery codes; the old ones stop working."""
    return RecoveryCodes(
        recovery_codes=mfa_service.regenerate_recovery_codes(db, user, data.password, data.code)
    )
