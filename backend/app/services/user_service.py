"""Admin-managed user accounts.

Distinct from auth_service: that module is "how you get a session"
(register/login/logout), this one is "how an admin manages other people's
accounts" once the app already has its first user.
"""

import secrets

from sqlalchemy.orm import Session

from app.core import password_policy
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.user import User
from app.repositories import user_repository
from app.schemas.user import UserAccountabilities, UserCreate, UserUpdate
from app.services import audit_service, auth_service

ENTITY_TYPE = "User"


def list_users(db: Session) -> list[User]:
    return user_repository.list_all(db)


def get_accountabilities(db: Session, user_id: int) -> UserAccountabilities:
    """Everything this user is personally accountable for. Deactivating them
    is allowed -- cutting off access can't wait on paperwork -- but nobody may
    approve in their place, so whatever they own is stuck until it is
    reassigned. Surfaced before the act rather than discovered afterwards.

    Imported inside the function to keep this module free of service-layer
    imports, the way the other cross-service reaches in this codebase do."""
    from app.core import risk_scoring
    from app.repositories import ai_system_lifecycle_repository, sheet_repository
    from app.services import (
        ai_system_inventory_service,
        data_inventory_service,
        governance_role_service,
        risk_assessment_service,
    )

    _get_or_raise(db, user_id)
    owner_key = str(user_id)

    ai_system_names = {
        row.id: str(row.data.get("name") or f"AI System #{row.id}")
        for row in ai_system_inventory_service.list_rows(db, include_archived=True)
    }
    ai_systems_owned = [
        ai_system_names.get(lifecycle.ai_system_row_id, f"AI System #{lifecycle.ai_system_row_id}")
        for lifecycle in ai_system_lifecycle_repository.list_all(db)
        if lifecycle.owner_id == user_id
    ]

    datasets_owned = [
        str(row.data.get("dataset_name") or f"Dataset #{row.id}")
        for row in data_inventory_service.list_rows(db)
        if str(row.data.get("data_owner") or "").strip() == owner_key
    ]

    open_risk_items = 0
    for risk_assessment in risk_assessment_service.list_risk_assessments(db):
        for row in sheet_repository.list_rows(db, risk_assessment.sheet_id):
            if str(row.data.get("risk_owner") or "").strip() != owner_key:
                continue
            if not risk_scoring.is_treated(row.data.get("status")):
                open_risk_items += 1

    return UserAccountabilities(
        governance_roles=[
            role.name for role in governance_role_service.list_roles_for_user(db, user_id)
        ],
        ai_systems_owned=sorted(ai_systems_owned),
        datasets_owned=sorted(datasets_owned),
        open_risk_items=open_risk_items,
    )


def _get_or_raise(db: Session, user_id: int) -> User:
    user = user_repository.get(db, user_id)
    if user is None:
        raise NotFoundError("User", user_id)
    return user


def create_user(db: Session, data: UserCreate, actor_id: int | None) -> User:
    if "@" not in data.email:
        raise ValidationError("Enter a valid email address.")
    email = data.email.strip().lower()
    if user_repository.get_by_email(db, email) is not None:
        raise ConflictError(f"A user with email {email} already exists.")
    password_policy.require(data.password, email=email, name=data.name)

    # The administrator chose this password, so the person must replace it
    # before doing anything else.
    user = User(
        name=data.name,
        email=email,
        password_hash=hash_password(data.password),
        role=data.role,
        must_change_password=True,
        temporary_password_expires_at=auth_service.temporary_password_deadline(),
    )
    user = user_repository.create(db, user)
    audit_service.log(
        db, ENTITY_TYPE, user.id, "created", actor_id, {"email": user.email, "role": user.role}
    )
    return user


def update_user(db: Session, user_id: int, data: UserUpdate, actor_id: int | None) -> User:
    if user_id == actor_id:
        raise ConflictError("You can't change your own role or active status; ask another admin.")

    user = _get_or_raise(db, user_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(user, field, value)

    user = user_repository.save(db, user)
    audit_service.log(db, ENTITY_TYPE, user.id, "updated", actor_id, changes)
    # What an open session was allowed to do has changed, so none of them
    # is left running on the old terms.
    if "role" in changes or changes.get("is_active") is False:
        auth_service.end_sessions(db, user.id)
    return user


def temporary_password(email: str, name: str) -> str:
    """A random one-time password. It never starts with a symbol, so a
    spreadsheet that is handed the list will not mistake it for a formula."""
    while True:
        candidate = secrets.token_urlsafe(12)
        if candidate[0].isalnum() and (
            password_policy.problem_with(candidate, email=email, name=name) is None
        ):
            return candidate


def reset_password(db: Session, user_id: int, actor_id: int) -> str:
    """For someone who is locked out or has forgotten their password: sets a
    temporary one, signs them out everywhere, and returns it -- for the
    administrator to pass on once. It is never stored in readable form, and
    the person must replace it at their next sign-in."""
    if user_id == actor_id:
        raise ConflictError("Change your own password from your account page instead.")
    user = _get_or_raise(db, user_id)
    temporary = temporary_password(user.email, user.name)
    auth_service.replace_password(db, user, temporary, must_change=True)
    ended = auth_service.end_sessions(db, user.id)
    audit_service.log(
        db, ENTITY_TYPE, user.id, "password_reset", actor_id, {"sessions_ended": ended}
    )
    return temporary
