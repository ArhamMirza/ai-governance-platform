from collections.abc import Callable, Generator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.framework_reference_data import as_rows
from app.core.security import hash_password
from app.dependencies import get_current_user
from app.main import app
from app.models.framework_control import FrameworkControl
from app.models.framework_soa_entry import FrameworkSoaEntry
from app.models.user import User, UserRole
from app.services import evidence_service

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def evidence_storage_dir(tmp_path, monkeypatch):
    fake_settings = SimpleNamespace(evidence_storage_dir=str(tmp_path))
    monkeypatch.setattr(evidence_service, "get_settings", lambda: fake_settings)
    return tmp_path


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        # Mirrors the alembic migration's data seed -- create_all only builds
        # the schema, so reference data has to be inserted separately here.
        session.bulk_insert_mappings(FrameworkControl, as_rows())
        session.commit()

        annex_a_ids = session.scalars(
            select(FrameworkControl.id).where(FrameworkControl.category == "annex_a_control")
        ).all()
        session.bulk_insert_mappings(
            FrameworkSoaEntry,
            [{"framework_control_id": control_id} for control_id in annex_a_ids],
        )
        session.commit()

        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _make_user(db_session: Session, **overrides) -> User:
    defaults = dict(
        name="Test User",
        email="test@example.com",
        password_hash=hash_password("password123"),
        role=UserRole.ADMIN,
    )
    defaults.update(overrides)
    user = User(**defaults)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def test_user(db_session: Session) -> User:
    return _make_user(db_session)


@pytest.fixture()
def second_user(db_session: Session) -> User:
    """A distinct admin, for segregation-of-duties tests: whoever submits a
    Policy/Procedure for review can't be the one who approves it, so those
    flows need a second real user to switch to mid-test."""
    return _make_user(db_session, name="Second User", email="second@example.com")


@pytest.fixture()
def make_user(db_session: Session) -> Callable[..., User]:
    """Factory for role-specific users in RBAC tests, e.g.
    make_user(role=UserRole.VIEWER). Emails auto-increment so callers don't
    need to pick unique ones."""
    counter = {"n": 0}

    def _make(**overrides) -> User:
        counter["n"] += 1
        overrides.setdefault("name", f"User {counter['n']}")
        overrides.setdefault("email", f"user{counter['n']}@example.com")
        return _make_user(db_session, **overrides)

    return _make


@pytest.fixture()
def login_as() -> Callable[[User], None]:
    """Switches the identity `client` authenticates as, for tests that need
    more than one user (e.g. submit as test_user, approve as second_user)."""

    def _login_as(user: User) -> None:
        app.dependency_overrides[get_current_user] = lambda: user

    return _login_as


@pytest.fixture()
def client(db_session: Session, test_user: User) -> Generator[TestClient, None, None]:
    """Authenticated as test_user -- almost every route requires a session,
    and most tests care about the feature under test, not the login flow.
    Use unauthenticated_client for auth itself and for 401 assertions."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def unauthenticated_client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
