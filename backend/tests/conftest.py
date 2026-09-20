from collections.abc import Callable, Generator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import embeddings, ocr, reranking, vector_store
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

# Text an OCR stub should "read" out of a fake image, so a test can write a
# picture of a document without shipping a picture of a document.
OCR_MARKER = b"OCR:"


def fake_image(text: str) -> bytes:
    """Bytes that the stubbed OCR reads back as ``text``."""
    return OCR_MARKER + text.encode()


def _hashing_vector(text: str) -> list[float]:
    """A deterministic stand-in for a real embedding.

    Words are hashed into dimensions and the result normalised, so texts that
    share vocabulary land near each other. That is enough to exercise every
    line of the retrieval path; it is not a claim about semantics, and no
    test here asserts one.
    """
    import math
    import re
    import zlib

    vector = [0.0] * embeddings.DIMENSIONS
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        # crc32, not hash(): Python randomises string hashing per process, so
        # hash() would move words between dimensions on every run and make
        # which words happen to collide -- and therefore the tests that turn
        # on it -- differ run to run.
        vector[zlib.crc32(word.encode()) % embeddings.DIMENSIONS] += 1.0
    length = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / length for v in vector]


@pytest.fixture(autouse=True)
def local_models_are_stubbed(monkeypatch):
    """No test downloads or runs a real model.

    The embedder, the reranker and the OCR engine all fetch weights on first
    use. Left real, the suite would pull hundreds of megabytes on a cold CI
    runner and fail whenever the network did -- so all three are replaced
    with stubs, and the real ones are exercised by hand.

    The reranker's stub is "unavailable" rather than a fake scorer: unlike
    the embedder's hashing vector, there's no cheap deterministic stand-in
    for cross-encoder relevance that wouldn't just be asserting its own
    fake logic. Leaving it unavailable means retrieval falls back to fusion
    order -- the behaviour every existing retrieval test already assumes --
    and the tests that actually exercise reranking install their own stub
    for `reranking.rerank` locally.
    """
    monkeypatch.setattr(
        embeddings, "embed_passages", lambda texts: [_hashing_vector(t) for t in texts]
    )
    monkeypatch.setattr(embeddings, "embed_query", lambda text: _hashing_vector(text))
    monkeypatch.setattr(reranking, "rerank", lambda query, passages: None)
    monkeypatch.setattr(ocr, "available", lambda: True)
    monkeypatch.setattr(
        ocr,
        "read_image",
        lambda data: data[len(OCR_MARKER) :].decode() if data.startswith(OCR_MARKER) else "",
    )


def create_search_tables(engine) -> None:
    """The FTS5 and sqlite-vec tables, which create_all cannot make.

    They are virtual tables built by raw DDL in the migration, so a schema
    built from the models alone is missing exactly the two tables document
    search reads from.
    """
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(text)"
        )
        if vector_store.vectors_available():
            dimensions = vector_store.EMBEDDING_DIMENSIONS
            connection.exec_driver_sql(
                "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vectors USING vec0("
                f"chunk_id INTEGER PRIMARY KEY, embedding FLOAT[{dimensions}])"
            )


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
    # Before anything connects: StaticPool keeps one connection for the whole
    # fixture, so a listener added after the first connect never fires for it.
    vector_store.register(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    create_search_tables(engine)

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
