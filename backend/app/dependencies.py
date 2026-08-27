from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AuthenticationError
from app.models.user import User
from app.services import auth_service

SESSION_COOKIE_NAME = "session_token"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = auth_service.get_user_for_token(db, token)
    if user is None:
        raise AuthenticationError()
    return user


def get_current_actor_id(user: User = Depends(get_current_user)) -> int:
    return user.id
