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
        content="v1 content",
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

    result = policy_service.create_policy(
        db, PolicyCreate(title="New Policy", content="body"), actor_id=7
    )

    assert result.status == PolicyStatus.DRAFT
    assert result.version == 1
    mock_repo.add_version.assert_called_once()
    added_version = mock_repo.add_version.call_args[0][1]
    assert added_version.version_no == 1
    assert added_version.change_note == "Initial draft"
    mock_audit.log.assert_called_once()


@patch("app.services.policy_service.audit_service")
@patch("app.services.policy_service.policy_repository")
def test_update_policy_bumps_version_when_content_changes(mock_repo, mock_audit, db) -> None:
    policy = make_policy()
    mock_repo.get.return_value = policy
    mock_repo.save.side_effect = lambda _db, p: p

    result = policy_service.update_policy(
        db, 1, PolicyUpdate(content="v2 content", change_note="revised wording"), actor_id=3
    )

    assert result.version == 2
    mock_repo.add_version.assert_called_once()
    added_version = mock_repo.add_version.call_args[0][1]
    assert added_version.version_no == 2
    assert added_version.change_note == "revised wording"


@patch("app.services.policy_service.audit_service")
@patch("app.services.policy_service.policy_repository")
def test_update_policy_does_not_bump_version_when_content_unchanged(
    mock_repo, mock_audit, db
) -> None:
    policy = make_policy()
    mock_repo.get.return_value = policy
    mock_repo.save.side_effect = lambda _db, p: p

    result = policy_service.update_policy(db, 1, PolicyUpdate(title="Renamed"), actor_id=3)

    assert result.version == 1
    mock_repo.add_version.assert_not_called()


@patch("app.services.policy_service.audit_service")
@patch("app.services.policy_service.policy_repository")
def test_update_policy_rejects_edit_when_not_draft(mock_repo, mock_audit, db) -> None:
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
