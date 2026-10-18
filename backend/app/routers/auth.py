from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.dependencies import SESSION_COOKIE_NAME, get_session_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    RegistrationStatus,
    SessionsEnded,
    UserRead,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_MAX_AGE_SECONDS = int(auth_service.SESSION_LIFETIME.total_seconds())


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


@router.get("/registration-status", response_model=RegistrationStatus)
def registration_status(db: Session = Depends(get_db)) -> RegistrationStatus:
    return RegistrationStatus(registration_open=auth_service.registration_open(db))


@router.post("/register", response_model=UserRead, status_code=201)
def register(data: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> UserRead:
    user = auth_service.register(db, data)
    token = auth_service.create_session(db, user)
    _set_session_cookie(response, token)
    return user


@router.post("/login", response_model=UserRead)
def login(
    data: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> UserRead:
    ip = request.client.host if request.client else None
    user = auth_service.authenticate(db, data, ip)
    token = auth_service.create_session(db, user)
    _set_session_cookie(response, token)
    return user


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    auth_service.revoke_session(db, token)
    response.delete_cookie(SESSION_COOKIE_NAME)


# These use get_session_user, not get_current_user: they are the routes
# someone who must still choose a new password is allowed to reach.
@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_session_user)) -> UserRead:
    return user


@router.post("/change-password", response_model=UserRead)
def change_password(
    data: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_session_user),
) -> UserRead:
    """Needs the current password, and signs every other device out."""
    return auth_service.change_password(
        db, user, data, keep_token=request.cookies.get(SESSION_COOKIE_NAME)
    )


@router.post("/sign-out-everywhere", response_model=SessionsEnded)
def sign_out_everywhere(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_session_user),
) -> SessionsEnded:
    ended = auth_service.sign_out_everywhere(
        db, user, keep_token=request.cookies.get(SESSION_COOKIE_NAME)
    )
    return SessionsEnded(other_sessions_ended=ended)
