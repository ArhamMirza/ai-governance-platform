from collections.abc import Callable, Generator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.framework_reference_data import as_rows
from app.core.governance_role_seed_data import DEFAULT_ROLES
from app.core.security import hash_password
from app.dependencies import get_current_user
from app.main import app
from app.models.framework_control import FrameworkControl
from app.models.framework_soa_entry import FrameworkSoaEntry
from app.models.governance_role import GovernanceRole
from app.models.user import User, UserRole
from app.services import evidence_service, governance_role_service

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def evidence_storage_dir(tmp_path, monkeypatch):
    fake_settings = SimpleNamespace(evidence_storage_dir=str(tmp_path))
    monkeypatch.setattr(evidence_service, "get_settings", lambda: fake_settings)
    return tmp_path


def seed_reference_data(session: Session) -> None:
    """Mirrors the alembic migrations' data seed -- create_all only builds the
    schema, so reference data has to be inserted separately. Shared with the
    concurrency suite, which builds its own engine (see
    tests/concurrency/conftest.py) but needs the same starting point."""
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

    caigo = GovernanceRole(
        name=DEFAULT_ROLES[0][0],
        responsibilities=DEFAULT_ROLES[0][1],
        max_holders=DEFAULT_ROLES[0][2],
    )
    session.add(caigo)
    session.commit()
    session.add_all(
        GovernanceRole(name=name, responsibilities=responsibilities, max_holders=max_holders,
                       parent_role_id=caigo.id)
        for name, responsibilities, max_holders in DEFAULT_ROLES[1:]
    )
    session.commit()


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
        seed_reference_data(session)
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
def make_caigo(db_session: Session) -> Callable[[User], None]:
    """Assigns a user as Chief AI Governance Officer -- tests exercising the
    CAIGO-gated approval flow need a real holder, since approval now checks
    governance_role_service.require_caigo rather than just admin/not-admin."""

    def _make_caigo(user: User) -> None:
        role = db_session.query(GovernanceRole).filter_by(name=DEFAULT_ROLES[0][0]).one()
        governance_role_service.assign_user(db_session, role.id, user.id, actor_id=None)

    return _make_caigo


@pytest.fixture()
def caigo_admin(db_session: Session, make_user: Callable[..., User]) -> User:
    """A dedicated admin holding the Chief AI Governance Officer role --
    for multi-stage lifecycle tests (deployment then retirement approval)
    that need the *same* CAIGO identity reusable across several approval
    calls, since CAIGO is capped at one holder."""
    admin = make_user(role=UserRole.ADMIN)
    role = db_session.query(GovernanceRole).filter_by(name=DEFAULT_ROLES[0][0]).one()
    governance_role_service.assign_user(db_session, role.id, admin.id, actor_id=None)
    return admin


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
