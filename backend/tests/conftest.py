from collections.abc import Generator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.framework_reference_data import as_rows
from app.main import app
from app.models.framework_control import FrameworkControl
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
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
