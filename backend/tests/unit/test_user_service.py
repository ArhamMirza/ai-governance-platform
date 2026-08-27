import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.services import user_service


def test_create_user(db_session: Session) -> None:
    user = user_service.create_user(
        db_session,
        UserCreate(name="Ada", email="ada@example.com", password="supersecret1"),
        actor_id=None,
    )

    assert user.email == "ada@example.com"
    assert user.role == UserRole.CONTRIBUTOR
    assert user.is_active is True
    assert user.password_hash != "supersecret1"


def test_create_user_with_an_explicit_role(db_session: Session) -> None:
    user = user_service.create_user(
        db_session,
        UserCreate(
            name="Ada", email="ada@example.com", password="supersecret1", role=UserRole.VIEWER
        ),
        actor_id=None,
    )

    assert user.role == UserRole.VIEWER


def test_create_user_lowercases_email(db_session: Session) -> None:
    user = user_service.create_user(
        db_session,
        UserCreate(name="Ada", email="  Ada@Example.com  ", password="supersecret1"),
        actor_id=None,
    )

    assert user.email == "ada@example.com"


def test_create_user_rejects_a_duplicate_email(db_session: Session) -> None:
    user_service.create_user(
        db_session,
        UserCreate(name="Ada", email="ada@example.com", password="supersecret1"),
        actor_id=None,
    )

    with pytest.raises(ConflictError):
        user_service.create_user(
            db_session,
            UserCreate(name="Ada Two", email="ada@example.com", password="supersecret1"),
            actor_id=None,
        )


def test_create_user_rejects_an_invalid_email(db_session: Session) -> None:
    with pytest.raises(ValidationError):
        user_service.create_user(
            db_session,
            UserCreate(name="Ada", email="not-an-email", password="supersecret1"),
            actor_id=None,
        )


def test_list_users(db_session: Session) -> None:
    user_service.create_user(
        db_session,
        UserCreate(name="Ada", email="ada@example.com", password="supersecret1"),
        actor_id=None,
    )
    user_service.create_user(
        db_session,
        UserCreate(name="Bob", email="bob@example.com", password="supersecret1"),
        actor_id=None,
    )

    users = user_service.list_users(db_session)

    assert {u.email for u in users} == {"ada@example.com", "bob@example.com"}


def test_update_user_role(db_session: Session) -> None:
    admin = User(name="Admin", email="admin@example.com", password_hash="x", role=UserRole.ADMIN)
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    user = user_service.create_user(
        db_session,
        UserCreate(name="Ada", email="ada@example.com", password="supersecret1"),
        actor_id=None,
    )

    updated = user_service.update_user(
        db_session, user.id, UserUpdate(role=UserRole.ADMIN), actor_id=admin.id
    )

    assert updated.role == UserRole.ADMIN


def test_update_user_deactivates(db_session: Session) -> None:
    admin = User(name="Admin", email="admin@example.com", password_hash="x", role=UserRole.ADMIN)
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    user = user_service.create_user(
        db_session,
        UserCreate(name="Ada", email="ada@example.com", password="supersecret1"),
        actor_id=None,
    )

    updated = user_service.update_user(
        db_session, user.id, UserUpdate(is_active=False), actor_id=admin.id
    )

    assert updated.is_active is False


def test_update_user_raises_for_a_missing_user(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        user_service.update_user(db_session, 999, UserUpdate(is_active=False), actor_id=1)


def test_cannot_change_your_own_role_or_active_status(db_session: Session) -> None:
    admin = User(name="Admin", email="admin@example.com", password_hash="x", role=UserRole.ADMIN)
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    with pytest.raises(ConflictError):
        user_service.update_user(
            db_session, admin.id, UserUpdate(is_active=False), actor_id=admin.id
        )
