import pytest

from app.core.permissions import Action, has_permission
from app.models.user import UserRole


@pytest.mark.parametrize(
    ("role", "allowed"),
    [
        (UserRole.VIEWER, {Action.VIEW}),
        (UserRole.CONTRIBUTOR, {Action.VIEW, Action.EDIT}),
        (
            UserRole.ADMIN,
            {Action.VIEW, Action.EDIT, Action.APPROVE, Action.MANAGE_USERS, Action.MANAGE_SETTINGS},
        ),
    ],
)
def test_role_permits_exactly_its_actions(role: UserRole, allowed: set[Action]) -> None:
    for action in Action:
        assert has_permission(role, action) is (action in allowed)


def test_unknown_role_permits_nothing() -> None:
    for action in Action:
        assert has_permission("not-a-real-role", action) is False


def test_viewer_cannot_edit() -> None:
    assert has_permission(UserRole.VIEWER, Action.EDIT) is False


def test_contributor_cannot_approve() -> None:
    assert has_permission(UserRole.CONTRIBUTOR, Action.APPROVE) is False


def test_contributor_cannot_manage_users_or_settings() -> None:
    assert has_permission(UserRole.CONTRIBUTOR, Action.MANAGE_USERS) is False
    assert has_permission(UserRole.CONTRIBUTOR, Action.MANAGE_SETTINGS) is False


def test_admin_can_do_everything() -> None:
    for action in Action:
        assert has_permission(UserRole.ADMIN, action) is True
