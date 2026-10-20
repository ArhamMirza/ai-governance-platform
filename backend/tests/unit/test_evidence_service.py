import io
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core import evidence_files
from app.core.exceptions import NotFoundError, ValidationError
from app.models.evidence import Evidence
from app.services import evidence_service


def make_upload_file(filename: str, content: bytes, content_type: str = "text/plain"):
    return SimpleNamespace(filename=filename, content_type=content_type, file=io.BytesIO(content))


def make_evidence(**overrides) -> Evidence:
    defaults = dict(
        id=1,
        entity_type="Policy",
        entity_id=10,
        folder_id=None,
        filename="doc.pdf",
        content_type="application/pdf",
        size_bytes=3,
        storage_path="/tmp/does-not-exist-doc.pdf",
        description=None,
        uploaded_by=None,
    )
    defaults.update(overrides)
    return Evidence(**defaults)


@pytest.fixture()
def db() -> MagicMock:
    return MagicMock()


@pytest.fixture(autouse=True)
def storage_dir(tmp_path, monkeypatch):
    fake_settings = SimpleNamespace(evidence_storage_dir=str(tmp_path))
    monkeypatch.setattr(evidence_files, "get_settings", lambda: fake_settings)
    return tmp_path


@patch("app.services.evidence_service.audit_service")
@patch("app.services.evidence_service.evidence_repository")
def test_upload_evidence_writes_file_and_creates_record(mock_repo, mock_audit, db) -> None:
    mock_repo.create.side_effect = lambda _db, evidence: evidence
    upload = make_upload_file("report.pdf", b"pdf-bytes", "application/pdf")

    result = evidence_service.upload_evidence(
        db, "Policy", 10, None, upload, description="Q1 report", actor_id=1
    )

    assert result.filename == "report.pdf"
    assert result.size_bytes == len(b"pdf-bytes")
    mock_audit.log.assert_called_once()


def test_upload_evidence_rejects_disallowed_extension(db) -> None:
    upload = make_upload_file("virus.exe", b"x")

    with pytest.raises(ValidationError):
        evidence_service.upload_evidence(db, "Policy", 10, None, upload, None, actor_id=1)


def test_upload_evidence_rejects_oversized_file(db) -> None:
    upload = make_upload_file("big.pdf", b"x" * (evidence_service.MAX_SIZE_BYTES + 1))

    with pytest.raises(ValidationError):
        evidence_service.upload_evidence(db, "Policy", 10, None, upload, None, actor_id=1)


@patch("app.services.evidence_service.folder_repository")
def test_upload_evidence_rejects_folder_from_different_entity(mock_folder_repo, db) -> None:
    mock_folder_repo.get.return_value = SimpleNamespace(entity_type="Procedure", entity_id=99)
    upload = make_upload_file("report.pdf", b"pdf-bytes")

    with pytest.raises(ValidationError):
        evidence_service.upload_evidence(db, "Policy", 10, 5, upload, None, actor_id=1)


@patch("app.services.evidence_service.evidence_repository")
def test_get_evidence_raises_not_found(mock_repo, db) -> None:
    mock_repo.get.return_value = None

    with pytest.raises(NotFoundError):
        evidence_service.get_evidence(db, 999)


@patch("app.services.evidence_service.audit_service")
@patch("app.services.evidence_service.evidence_repository")
def test_delete_evidence_removes_file_and_record(mock_repo, mock_audit, db, storage_dir) -> None:
    file_path = storage_dir / "existing.pdf"
    file_path.write_bytes(b"content")
    evidence = make_evidence(storage_path=str(file_path))
    mock_repo.get.return_value = evidence

    evidence_service.delete_evidence(db, 1, actor_id=1)

    assert not file_path.exists()
    mock_repo.delete.assert_called_once_with(db, evidence)
    mock_audit.log.assert_called_once()


@patch("app.services.evidence_service.audit_service")
@patch("app.services.evidence_service.evidence_repository")
def test_delete_evidence_tolerates_missing_file(mock_repo, mock_audit, db) -> None:
    evidence = make_evidence(storage_path="/does/not/exist.pdf")
    mock_repo.get.return_value = evidence

    evidence_service.delete_evidence(db, 1, actor_id=1)

    mock_repo.delete.assert_called_once_with(db, evidence)
