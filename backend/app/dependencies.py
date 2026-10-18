from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.permissions import Action, has_permission
from app.models.user import User, UserRole
from app.services import ai_usage_service, auth_service

SESSION_COOKIE_NAME = "session_token"
PASSWORD_CHANGE_REQUIRED = "You need to choose a new password before you can continue."


def get_session_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Whoever holds a valid session -- including someone who still has to
    choose a new password. Only the few routes that let them do that, or
    sign out, use this directly; everything else goes through
    get_current_user."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = auth_service.get_user_for_token(db, token)
    if user is None or not user.is_active:
        raise AuthenticationError()
    return user


def get_current_user(user: User = Depends(get_session_user)) -> User:
    if user.must_change_password:
        raise AuthorizationError(PASSWORD_CHANGE_REQUIRED)
    return user


def get_internal_user(user: User = Depends(get_current_user)) -> User:
    """Any signed-in user of the platform proper -- everyone but an employee.
    Every business router is mounted behind this (see app.main._protected), so
    an employee's login reaches only the routes that opt in with plain
    get_current_user, and a router added later is closed to them by default.
    A 403 rather than a 404: the route exists, they just can't use it."""
    if user.role == UserRole.EMPLOYEE:
        raise AuthorizationError("This account can only use the employee home.")
    return user


def require_concern_handler(user: User = Depends(get_internal_user)) -> User:
    """Who may read and act on concerns: administrators. Not every editor --
    a concern can name colleagues or describe misconduct.

    The Chief AI Governance Officer, and anyone standing in for them, must
    themselves be admin accounts (governance_role_service enforces it), so
    "admins and the CAIGO" is simply "admins". A narrower set -- a dedicated
    concerns officer who needn't be an admin -- would be a governance role
    checked here instead."""
    if user.role != UserRole.ADMIN:
        raise AuthorizationError("Only administrators can handle concerns.")
    return user


def require_agent_key(request: Request, db: Session = Depends(get_db)) -> None:
    """For the browser extension's routes: the organization's enrollment key,
    sent as `Authorization: Bearer <key>`. A session is neither needed nor
    accepted -- these routes are not part of the signed-in app."""
    header = request.headers.get("authorization", "")
    presented = header[7:].strip() if header.lower().startswith("bearer ") else None
    caller = request.client.host if request.client else "unknown"
    ai_usage_service.authenticate_agent(db, presented, caller)


def _require(action: Action):
    """A Depends() factory: returns the current user if their role permits
    `action`, otherwise raises 403. One factory call per distinct action
    below, rather than a parameterized route dependency, so each call site
    reads as "this route needs X" without a runtime action argument."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, action):
            raise AuthorizationError(f"Your role ('{user.role}') doesn't permit this action.")
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
