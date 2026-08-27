from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError, ValidationError
from app.core.security import hash_session_token
from app.models.session import Session as UserSession
from app.repositories import session_repository
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services import auth_service


def make_register(**overrides) -> RegisterRequest:
    defaults = dict(name="Ada Lovelace", email="ada@example.com", password="supersecret1")
    defaults.update(overrides)
    return RegisterRequest(**defaults)


def test_registration_open_before_any_user_exists(db_session: Session) -> None:
    assert auth_service.registration_open(db_session) is True


def test_register_creates_the_first_user(db_session: Session) -> None:
    user = auth_service.register(db_session, make_register())

    assert user.email == "ada@example.com"
    assert user.password_hash != "supersecret1"


def test_register_lowercases_and_trims_email(db_session: Session) -> None:
    user = auth_service.register(db_session, make_register(email="  Ada@Example.com  "))

    assert user.email == "ada@example.com"


def test_registration_closes_after_the_first_user(db_session: Session) -> None:
    auth_service.register(db_session, make_register())

    assert auth_service.registration_open(db_session) is False
    with pytest.raises(ConflictError):
        auth_service.register(db_session, make_register(email="second@example.com"))


def test_register_rejects_an_invalid_email(db_session: Session) -> None:
    with pytest.raises(ValidationError):
        auth_service.register(db_session, make_register(email="not-an-email"))


def test_authenticate_succeeds_with_correct_credentials(db_session: Session) -> None:
    auth_service.register(db_session, make_register())

    user = auth_service.authenticate(
        db_session, LoginRequest(email="ada@example.com", password="supersecret1")
    )

    assert user.email == "ada@example.com"


def test_authenticate_is_case_insensitive_on_email(db_session: Session) -> None:
    auth_service.register(db_session, make_register())

    user = auth_service.authenticate(
        db_session, LoginRequest(email="ADA@example.com", password="supersecret1")
    )

    assert user.email == "ada@example.com"


def test_authenticate_rejects_wrong_password(db_session: Session) -> None:
    auth_service.register(db_session, make_register())

    with pytest.raises(AuthenticationError):
        auth_service.authenticate(
            db_session, LoginRequest(email="ada@example.com", password="wrong")
        )


def test_authenticate_rejects_unknown_email(db_session: Session) -> None:
    with pytest.raises(AuthenticationError):
        auth_service.authenticate(
            db_session, LoginRequest(email="nobody@example.com", password="whatever1")
        )


def test_create_session_then_resolve_the_user_from_the_token(db_session: Session) -> None:
    user = auth_service.register(db_session, make_register())

    token = auth_service.create_session(db_session, user)
    resolved = auth_service.get_user_for_token(db_session, token)

    assert resolved is not None
    assert resolved.id == user.id


def test_get_user_for_token_with_no_token(db_session: Session) -> None:
    assert auth_service.get_user_for_token(db_session, None) is None
    assert auth_service.get_user_for_token(db_session, "") is None


def test_get_user_for_token_with_an_unknown_token(db_session: Session) -> None:
    assert auth_service.get_user_for_token(db_session, "not-a-real-token") is None


def test_get_user_for_token_with_an_expired_session_returns_none_and_deletes_it(
    db_session: Session,
) -> None:
    user = auth_service.register(db_session, make_register())
    token = "expired-token"
    session_repository.create(
        db_session,
        UserSession(
            token_hash=hash_session_token(token),
            user_id=user.id,
            expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1),
        ),
    )

    assert auth_service.get_user_for_token(db_session, token) is None
    assert session_repository.get_by_token_hash(db_session, hash_session_token(token)) is None


def test_revoke_session_invalidates_the_token(db_session: Session) -> None:
    user = auth_service.register(db_session, make_register())
    token = auth_service.create_session(db_session, user)

    auth_service.revoke_session(db_session, token)

    assert auth_service.get_user_for_token(db_session, token) is None


def test_revoke_session_with_no_token_is_a_no_op(db_session: Session) -> None:
    auth_service.revoke_session(db_session, None)
