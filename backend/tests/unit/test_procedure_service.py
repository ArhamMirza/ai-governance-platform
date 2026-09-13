from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import InvalidStatusTransitionError, NotFoundError
from app.models.procedure import Procedure, ProcedureStatus
from app.schemas.procedure import ProcedureCreate, ProcedureUpdate
from app.services import procedure_service


def make_procedure(**overrides) -> Procedure:
    defaults = dict(
        id=1,
        title="Test Procedure",
        description=None,
        owner_id=None,
        policy_id=None,
        effective_date=None,
        status=ProcedureStatus.DRAFT,
        version=1,
    )
    defaults.update(overrides)
    return Procedure(**defaults)


@pytest.fixture()
def db() -> MagicMock:
    return MagicMock()


@patch("app.services.procedure_service.audit_service")
@patch("app.services.procedure_service.procedure_repository")
def test_create_procedure_starts_as_draft_version_one(mock_repo, mock_audit, db) -> None:
    mock_repo.create.side_effect = lambda _db, procedure: procedure

    result = procedure_service.create_procedure(
        db, ProcedureCreate(title="New Procedure"), actor_id=7
    )

    assert result.status == ProcedureStatus.DRAFT
    assert result.version == 1
    mock_audit.log.assert_called_once()


@patch("app.services.procedure_service.audit_service")
@patch("app.services.procedure_service.policy_repository")
@patch("app.services.procedure_service.procedure_repository")
def test_create_procedure_links_to_existing_policy(
    mock_repo, mock_policy_repo, mock_audit, db
) -> None:
    mock_repo.create.side_effect = lambda _db, procedure: procedure
    mock_policy_repo.get.return_value = object()

    result = procedure_service.create_procedure(
        db, ProcedureCreate(title="New Procedure", policy_id=5), actor_id=7
    )

    assert result.policy_id == 5


@patch("app.services.procedure_service.policy_repository")
def test_create_procedure_rejects_missing_policy_link(mock_policy_repo, db) -> None:
    mock_policy_repo.get.return_value = None

    with pytest.raises(NotFoundError):
        procedure_service.create_procedure(
            db, ProcedureCreate(title="New Procedure", policy_id=999), actor_id=7
        )


@patch("app.services.procedure_service.audit_service")
@patch("app.services.procedure_service.procedure_repository")
def test_update_procedure_edits_metadata_without_bumping_version(
    mock_repo, mock_audit, db
) -> None:
    procedure = make_procedure()
    mock_repo.get.return_value = procedure
    mock_repo.save.side_effect = lambda _db, p: p

    result = procedure_service.update_procedure(
        db, 1, ProcedureUpdate(title="Renamed"), actor_id=3
    )

    assert result.title == "Renamed"
    assert result.version == 1


@patch("app.services.procedure_service.procedure_repository")
def test_update_procedure_rejects_edit_when_not_draft(mock_repo, db) -> None:
    procedure = make_procedure(status=ProcedureStatus.APPROVED)
    mock_repo.get.return_value = procedure

    with pytest.raises(InvalidStatusTransitionError):
        procedure_service.update_procedure(db, 1, ProcedureUpdate(title="Renamed"), actor_id=3)


@patch("app.services.procedure_service.procedure_repository")
def test_get_procedure_raises_not_found(mock_repo, db) -> None:
    mock_repo.get.return_value = None

    with pytest.raises(NotFoundError):
        procedure_service.get_procedure(db, 999)


def test_submit_for_review_transitions_draft_to_in_review(db_session) -> None:
    procedure = procedure_service.create_procedure(
        db_session, ProcedureCreate(title="Test Procedure"), actor_id=None
    )

    result = procedure_service.submit_for_review(db_session, procedure.id, actor_id=None)

    assert result.status == ProcedureStatus.IN_REVIEW


@patch("app.services.procedure_service.procedure_repository")
def test_submit_for_review_rejects_non_draft(mock_repo, db) -> None:
    procedure = make_procedure(status=ProcedureStatus.IN_REVIEW)
    mock_repo.get.return_value = procedure

    with pytest.raises(InvalidStatusTransitionError):
        procedure_service.submit_for_review(db, 1, actor_id=1)


def test_approve_procedure_transitions_in_review_to_approved(db_session) -> None:
    procedure = procedure_service.create_procedure(
        db_session, ProcedureCreate(title="Test Procedure"), actor_id=None
    )
    procedure_service.submit_for_review(db_session, procedure.id, actor_id=None)

    result = procedure_service.approve_procedure(db_session, procedure.id, actor_id=None)

    assert result.status == ProcedureStatus.APPROVED


@patch("app.services.procedure_service.procedure_repository")
def test_approve_procedure_rejects_non_in_review(mock_repo, db) -> None:
    procedure = make_procedure(status=ProcedureStatus.DRAFT)
    mock_repo.get.return_value = procedure

    with pytest.raises(InvalidStatusTransitionError):
        procedure_service.approve_procedure(db, 1, actor_id=1)


@patch("app.services.procedure_service.audit_service")
@patch("app.services.procedure_service.procedure_repository")
def test_delete_procedure_allowed_when_draft(mock_repo, mock_audit, db) -> None:
    procedure = make_procedure(status=ProcedureStatus.DRAFT)
    mock_repo.get.return_value = procedure

    procedure_service.delete_procedure(db, 1, actor_id=1)

    mock_repo.delete.assert_called_once_with(db, procedure)


@patch("app.services.procedure_service.procedure_repository")
def test_delete_procedure_rejected_when_not_draft(mock_repo, db) -> None:
    procedure = make_procedure(status=ProcedureStatus.APPROVED)
    mock_repo.get.return_value = procedure

    with pytest.raises(InvalidStatusTransitionError):
        procedure_service.delete_procedure(db, 1, actor_id=1)


@patch("app.services.procedure_service.audit_log_repository")
@patch("app.services.procedure_service.procedure_repository")
def test_list_document_history_filters_to_document_actions(
    mock_repo, mock_audit_repo, db
) -> None:
    procedure = make_procedure()
    mock_repo.get.return_value = procedure
    mock_audit_repo.list_for_entity.return_value = []

    procedure_service.list_document_history(db, 1)

    mock_audit_repo.list_for_entity.assert_called_once_with(
        db, "Procedure", 1, ["document_added", "document_removed"]
    )


@patch("app.services.procedure_service.procedure_repository")
def test_bump_version_if_draft_increments_when_draft(mock_repo, db) -> None:
    procedure = make_procedure(status=ProcedureStatus.DRAFT, version=1)
    mock_repo.get.return_value = procedure
    mock_repo.save.side_effect = lambda _db, p: p

    procedure_service.bump_version_if_draft(db, 1)

    assert procedure.version == 2


@patch("app.services.procedure_service.procedure_repository")
def test_bump_version_if_draft_noop_when_not_draft(mock_repo, db) -> None:
    procedure = make_procedure(status=ProcedureStatus.APPROVED, version=1)
    mock_repo.get.return_value = procedure

    procedure_service.bump_version_if_draft(db, 1)

    assert procedure.version == 1
    mock_repo.save.assert_not_called()
