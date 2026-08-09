from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import InvalidStatusTransitionError, NotFoundError
from app.models.policy import Policy, PolicyStatus
from app.schemas.policy import PolicyCreate, PolicyUpdate
from app.services import policy_service


def make_policy(**overrides) -> Policy:
    defaults = dict(
        id=1,
        title="Test Policy",
        description=None,
        owner_id=None,
        effective_date=None,
        status=PolicyStatus.DRAFT,
        version=1,
    )
    defaults.update(overrides)
    return Policy(**defaults)


@pytest.fixture()
def db() -> MagicMock:
    return MagicMock()


@patch("app.services.policy_service.audit_service")
@patch("app.services.policy_service.policy_repository")
def test_create_policy_starts_as_draft_version_one(mock_repo, mock_audit, db) -> None:
    mock_repo.create.side_effect = lambda _db, policy: policy

    result = policy_service.create_policy(db, PolicyCreate(title="New Policy"), actor_id=7)

    assert result.status == PolicyStatus.DRAFT
    assert result.version == 1
    mock_audit.log.assert_called_once()


@patch("app.services.policy_service.audit_service")
@patch("app.services.policy_service.policy_repository")
def test_update_policy_edits_metadata_without_bumping_version(mock_repo, mock_audit, db) -> None:
    policy = make_policy()
    mock_repo.get.return_value = policy
    mock_repo.save.side_effect = lambda _db, p: p

    result = policy_service.update_policy(db, 1, PolicyUpdate(title="Renamed"), actor_id=3)

    assert result.title == "Renamed"
    assert result.version == 1


@patch("app.services.policy_service.policy_repository")
def test_update_policy_rejects_edit_when_not_draft(mock_repo, db) -> None:
    policy = make_policy(status=PolicyStatus.APPROVED)
    mock_repo.get.return_value = policy

    with pytest.raises(InvalidStatusTransitionError):
        policy_service.update_policy(db, 1, PolicyUpdate(title="Renamed"), actor_id=3)


@patch("app.services.policy_service.policy_repository")
def test_get_policy_raises_not_found(mock_repo, db) -> None:
    mock_repo.get.return_value = None

    with pytest.raises(NotFoundError):
        policy_service.get_policy(db, 999)


@patch("app.services.policy_service.audit_service")
@patch("app.services.policy_service.policy_repository")
def test_submit_for_review_transitions_draft_to_in_review(mock_repo, mock_audit, db) -> None:
    policy = make_policy()
    mock_repo.get.return_value = policy
    mock_repo.save.side_effect = lambda _db, p: p

    result = policy_service.submit_for_review(db, 1, actor_id=1)

    assert result.status == PolicyStatus.IN_REVIEW


@patch("app.services.policy_service.policy_repository")
def test_submit_for_review_rejects_non_draft(mock_repo, db) -> None:
    policy = make_policy(status=PolicyStatus.IN_REVIEW)
    mock_repo.get.return_value = policy

    with pytest.raises(InvalidStatusTransitionError):
        policy_service.submit_for_review(db, 1, actor_id=1)


@patch("app.services.policy_service.audit_service")
@patch("app.services.policy_service.policy_repository")
def test_approve_policy_transitions_in_review_to_approved(mock_repo, mock_audit, db) -> None:
    policy = make_policy(status=PolicyStatus.IN_REVIEW)
    mock_repo.get.return_value = policy
    mock_repo.save.side_effect = lambda _db, p: p

    result = policy_service.approve_policy(db, 1, actor_id=1)

    assert result.status == PolicyStatus.APPROVED


@patch("app.services.policy_service.policy_repository")
def test_approve_policy_rejects_non_in_review(mock_repo, db) -> None:
    policy = make_policy(status=PolicyStatus.DRAFT)
    mock_repo.get.return_value = policy

    with pytest.raises(InvalidStatusTransitionError):
        policy_service.approve_policy(db, 1, actor_id=1)


@patch("app.services.policy_service.audit_service")
@patch("app.services.policy_service.policy_repository")
def test_delete_policy_allowed_when_draft(mock_repo, mock_audit, db) -> None:
    policy = make_policy(status=PolicyStatus.DRAFT)
    mock_repo.get.return_value = policy

    policy_service.delete_policy(db, 1, actor_id=1)

    mock_repo.delete.assert_called_once_with(db, policy)


@patch("app.services.policy_service.policy_repository")
def test_delete_policy_rejected_when_not_draft(mock_repo, db) -> None:
    policy = make_policy(status=PolicyStatus.APPROVED)
    mock_repo.get.return_value = policy

    with pytest.raises(InvalidStatusTransitionError):
        policy_service.delete_policy(db, 1, actor_id=1)


@patch("app.services.policy_service.audit_log_repository")
@patch("app.services.policy_service.policy_repository")
def test_list_document_history_filters_to_document_actions(mock_repo, mock_audit_repo, db) -> None:
    policy = make_policy()
    mock_repo.get.return_value = policy
    mock_audit_repo.list_for_entity.return_value = []

    policy_service.list_document_history(db, 1)

    mock_audit_repo.list_for_entity.assert_called_once_with(
        db, "Policy", 1, ["document_added", "document_removed"]
    )


@patch("app.services.policy_service.policy_repository")
def test_list_document_history_raises_not_found(mock_repo, db) -> None:
    mock_repo.get.return_value = None

    with pytest.raises(NotFoundError):
        policy_service.list_document_history(db, 999)


@patch("app.services.policy_service.policy_repository")
def test_bump_version_if_draft_increments_when_draft(mock_repo, db) -> None:
    policy = make_policy(status=PolicyStatus.DRAFT, version=1)
    mock_repo.get.return_value = policy
    mock_repo.save.side_effect = lambda _db, p: p

    policy_service.bump_version_if_draft(db, 1)

    assert policy.version == 2


@patch("app.services.policy_service.policy_repository")
def test_bump_version_if_draft_noop_when_not_draft(mock_repo, db) -> None:
    policy = make_policy(status=PolicyStatus.APPROVED, version=1)
    mock_repo.get.return_value = policy

    policy_service.bump_version_if_draft(db, 1)

    assert policy.version == 1
    mock_repo.save.assert_not_called()


@patch("app.services.policy_service.policy_repository")
def test_bump_version_if_draft_noop_when_policy_missing(mock_repo, db) -> None:
    mock_repo.get.return_value = None

    policy_service.bump_version_if_draft(db, 999)

    mock_repo.save.assert_not_called()
