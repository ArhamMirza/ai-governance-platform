"""Admin-managed user accounts.

Distinct from auth_service: that module is "how you get a session"
(register/login/logout), this one is "how an admin manages other people's
accounts" once the app already has its first user.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.user import User
from app.repositories import user_repository
from app.schemas.user import UserCreate, UserUpdate
from app.services import audit_service

ENTITY_TYPE = "User"


def list_users(db: Session) -> list[User]:
    return user_repository.list_all(db)


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

    user = User(
        name=data.name,
        email=email,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    user = user_repository.create(db, user)
    audit_service.log(
        db, ENTITY_TYPE, user.id, "created", actor_id, {"email": user.email, "role": user.role}
    )
    return user


def update_user(
    db: Session, user_id: int, data: UserUpdate, actor_id: int | None
) -> User:
    if user_id == actor_id:
        raise ConflictError(
            "You can't change your own role or active status; ask another admin."
        )

    user = _get_or_raise(db, user_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(user, field, value)

    user = user_repository.save(db, user)
    audit_service.log(db, ENTITY_TYPE, user.id, "updated", actor_id, changes)
    return user
