from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.folder import Folder
from app.schemas.folder import FolderCreate, FolderUpdate
from app.services import folder_service


def make_folder(**overrides) -> Folder:
    defaults = dict(id=1, entity_type="Policy", entity_id=10, parent_folder_id=None, name="Root")
    defaults.update(overrides)
    return Folder(**defaults)


@pytest.fixture()
def db() -> MagicMock:
    return MagicMock()


@patch("app.services.folder_service.audit_service")
@patch("app.services.folder_service.folder_repository")
def test_create_folder_at_root(mock_repo, mock_audit, db) -> None:
    mock_repo.create.side_effect = lambda _db, folder: folder

    result = folder_service.create_folder(
        db, FolderCreate(entity_type="Policy", entity_id=10, name="Signed Versions"), actor_id=1
    )

    assert result.name == "Signed Versions"
    assert result.parent_folder_id is None
    mock_audit.log.assert_called_once()


@patch("app.services.folder_service.audit_service")
@patch("app.services.folder_service.folder_repository")
def test_create_subfolder_with_matching_parent(mock_repo, mock_audit, db) -> None:
    parent = make_folder(id=5)
    mock_repo.get.return_value = parent
    mock_repo.create.side_effect = lambda _db, folder: folder

    result = folder_service.create_folder(
        db,
        FolderCreate(entity_type="Policy", entity_id=10, name="2026", parent_folder_id=5),
        actor_id=1,
    )

    assert result.parent_folder_id == 5


@patch("app.services.folder_service.folder_repository")
def test_create_subfolder_rejects_mismatched_parent_entity(mock_repo, db) -> None:
    parent = make_folder(id=5, entity_type="Procedure", entity_id=99)
    mock_repo.get.return_value = parent

    with pytest.raises(ValidationError):
        folder_service.create_folder(
            db,
            FolderCreate(entity_type="Policy", entity_id=10, name="2026", parent_folder_id=5),
            actor_id=1,
        )


@patch("app.services.folder_service.folder_repository")
def test_get_folder_raises_not_found(mock_repo, db) -> None:
    mock_repo.get.return_value = None

    with pytest.raises(NotFoundError):
        folder_service.get_folder(db, 999)


@patch("app.services.folder_service.audit_service")
@patch("app.services.folder_service.folder_repository")
def test_update_folder_renames(mock_repo, mock_audit, db) -> None:
    folder = make_folder()
    mock_repo.get.return_value = folder
    mock_repo.save.side_effect = lambda _db, f: f

    result = folder_service.update_folder(db, 1, FolderUpdate(name="Renamed"), actor_id=1)

    assert result.name == "Renamed"


@patch("app.services.folder_service.evidence_repository")
@patch("app.services.folder_service.audit_service")
@patch("app.services.folder_service.folder_repository")
def test_delete_empty_folder(mock_repo, mock_audit, mock_evidence_repo, db) -> None:
    folder = make_folder()
    mock_repo.get.return_value = folder
    mock_repo.has_children.return_value = False
    mock_evidence_repo.has_evidence_in_folder.return_value = False

    folder_service.delete_folder(db, 1, actor_id=1)

    mock_repo.delete.assert_called_once_with(db, folder)


@patch("app.services.folder_service.folder_repository")
def test_delete_folder_rejects_when_it_has_subfolders(mock_repo, db) -> None:
    folder = make_folder()
    mock_repo.get.return_value = folder
    mock_repo.has_children.return_value = True

    with pytest.raises(ConflictError):
        folder_service.delete_folder(db, 1, actor_id=1)


@patch("app.services.folder_service.evidence_repository")
@patch("app.services.folder_service.folder_repository")
def test_delete_folder_rejects_when_it_has_documents(mock_repo, mock_evidence_repo, db) -> None:
    folder = make_folder()
    mock_repo.get.return_value = folder
    mock_repo.has_children.return_value = False
    mock_evidence_repo.has_evidence_in_folder.return_value = True

    with pytest.raises(ConflictError):
        folder_service.delete_folder(db, 1, actor_id=1)
