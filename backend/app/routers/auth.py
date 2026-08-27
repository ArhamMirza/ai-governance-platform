from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.dependencies import SESSION_COOKIE_NAME, get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, RegistrationStatus, UserRead
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
def register(
    data: RegisterRequest, response: Response, db: Session = Depends(get_db)
) -> UserRead:
    user = auth_service.register(db, data)
    token = auth_service.create_session(db, user)
    _set_session_cookie(response, token)
    return user


@router.post("/login", response_model=UserRead)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserRead:
    user = auth_service.authenticate(db, data)
    token = auth_service.create_session(db, user)
    _set_session_cookie(response, token)
    return user


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    auth_service.revoke_session(db, token)
    response.delete_cookie(SESSION_COOKIE_NAME)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return user
