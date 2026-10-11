"""Role -> action permission table.

Four roles (app/models/user.py): admin, contributor, viewer, and employee --
which holds no action at all, because it is not an internal user. Deliberately a
flat lookup table rather than a hierarchy class, so "what can a contributor
do" is answerable by reading one dict, not tracing inheritance.
"""

from enum import StrEnum

from app.models.user import UserRole


class Action(StrEnum):
    VIEW = "view"
    # Create/update/delete/upload/tag/submit-for-review -- anything that
    # changes content but isn't a governance decision.
    EDIT = "edit"
    # The governance decision itself (Policy/Procedure approve). Kept
    # separate from EDIT so segregation-of-duties has a single action to
    # gate, independent of who's allowed to edit at all.
    APPROVE = "approve"
    MANAGE_USERS = "manage_users"
    # Org-wide settings that aren't tied to one document -- risk appetite
    # (risk criteria) today.
    MANAGE_SETTINGS = "manage_settings"


ROLE_PERMISSIONS: dict[str, frozenset[Action]] = {
    UserRole.VIEWER: frozenset({Action.VIEW}),
    UserRole.EMPLOYEE: frozenset(),
    UserRole.CONTRIBUTOR: frozenset({Action.VIEW, Action.EDIT}),
    UserRole.ADMIN: frozenset(
        {
            Action.VIEW,
            Action.EDIT,
            Action.APPROVE,
            Action.MANAGE_USERS,
            Action.MANAGE_SETTINGS,
        }
    ),
}


def has_permission(role: str, action: Action) -> bool:
    return action in ROLE_PERMISSIONS.get(role, frozenset())
