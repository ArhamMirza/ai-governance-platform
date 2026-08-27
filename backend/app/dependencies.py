from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.permissions import Action, has_permission
from app.models.user import User
from app.services import auth_service

SESSION_COOKIE_NAME = "session_token"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = auth_service.get_user_for_token(db, token)
    if user is None or not user.is_active:
        raise AuthenticationError()
    return user


def _require(action: Action):
    """A Depends() factory: returns the current user if their role permits
    `action`, otherwise raises 403. One factory call per distinct action
    below, rather than a parameterized route dependency, so each call site
    reads as "this route needs X" without a runtime action argument."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, action):
            raise AuthorizationError(
                f"Your role ('{user.role}') doesn't permit this action."
            )
        return user

    return dependency


require_edit_user = _require(Action.EDIT)
require_approve_user = _require(Action.APPROVE)
require_manage_users_user = _require(Action.MANAGE_USERS)
require_manage_settings_user = _require(Action.MANAGE_SETTINGS)


def get_current_actor_id(user: User = Depends(require_edit_user)) -> int:
    """Used by every create/update/delete endpoint, both for audit
    attribution and to enforce that the actor has edit rights at all."""
    return user.id


def get_current_approver_id(user: User = Depends(require_approve_user)) -> int:
    return user.id


def get_current_settings_actor_id(user: User = Depends(require_manage_settings_user)) -> int:
    return user.id
