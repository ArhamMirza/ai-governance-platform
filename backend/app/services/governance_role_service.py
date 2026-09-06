"""Organizational accountability, separate from (but partly linked to) the
technical admin/contributor/viewer permission a user holds -- see
CHIEF_AI_GOVERNANCE_OFFICER's admin-only rule below for where they connect.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.governance_role import GovernanceRole
from app.models.governance_role_assignment import GovernanceRoleAssignment
from app.models.user import User, UserRole
from app.repositories import governance_role_repository
from app.services import audit_service

ENTITY_TYPE = "GovernanceRole"
CHIEF_AI_GOVERNANCE_OFFICER = "Chief AI Governance Officer"


def _get_role_or_raise(db: Session, role_id: int) -> GovernanceRole:
    role = governance_role_repository.get(db, role_id)
    if role is None:
        raise NotFoundError("GovernanceRole", role_id)
    return role


def _get_user_or_raise(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User", user_id)
    return user


def list_roles(db: Session) -> list[GovernanceRole]:
    return governance_role_repository.list_all(db)


def get_role(db: Session, role_id: int) -> GovernanceRole:
    return _get_role_or_raise(db, role_id)


def create_role(
    db: Session,
    name: str,
    responsibilities: str,
    parent_role_id: int | None,
    max_holders: int | None,
    actor_id: int | None,
) -> GovernanceRole:
    if not name.strip():
        raise ValidationError("Give the role a name.")
    if governance_role_repository.get_by_name(db, name.strip()) is not None:
        raise ConflictError(f"A role named '{name}' already exists.")
    if parent_role_id is not None:
        _get_role_or_raise(db, parent_role_id)

    role = GovernanceRole(
        name=name.strip(),
        responsibilities=responsibilities,
        parent_role_id=parent_role_id,
        max_holders=max_holders,
    )
    role = governance_role_repository.create(db, role)
    audit_service.log(db, ENTITY_TYPE, role.id, "created", actor_id, {"name": role.name})
    return role


def _reject_cycle(db: Session, role_id: int, new_parent_id: int) -> None:
    """Walks up from the proposed parent to the root; if role_id turns up
    along the way, this reparenting would make the role its own ancestor --
    the self-reference check alone only catches the direct case (A -> A),
    not a deeper one (A -> B -> A)."""
    current: int | None = new_parent_id
    seen: set[int] = set()
    while current is not None:
        if current == role_id:
            raise ValidationError(
                "That would make this role report to one of its own descendants."
            )
        if current in seen:
            break  # An existing cycle elsewhere in the tree -- not this call's problem.
        seen.add(current)
        parent = governance_role_repository.get(db, current)
        current = parent.parent_role_id if parent is not None else None


def update_role(
    db: Session,
    role_id: int,
    name: str | None,
    responsibilities: str | None,
    parent_role_id: int | None,
    parent_role_set: bool,
    max_holders: int | None,
    max_holders_set: bool,
    actor_id: int | None,
) -> GovernanceRole:
    """parent_role_set/max_holders_set distinguish "leave unchanged" from
    "explicitly clear to None" for two nullable fields, the same way
    exclude_unset works for a Pydantic model_dump elsewhere in the app."""
    role = _get_role_or_raise(db, role_id)

    if name is not None and name.strip() != role.name:
        if governance_role_repository.get_by_name(db, name.strip()) is not None:
            raise ConflictError(f"A role named '{name}' already exists.")
        role.name = name.strip()
    if responsibilities is not None:
        role.responsibilities = responsibilities
    if parent_role_set:
        if parent_role_id == role_id:
            raise ValidationError("A role can't report to itself.")
        if parent_role_id is not None:
            _get_role_or_raise(db, parent_role_id)
            _reject_cycle(db, role_id, parent_role_id)
        role.parent_role_id = parent_role_id
    if max_holders_set:
        holder_count = governance_role_repository.count_holders(db, role_id)
        if max_holders is not None and max_holders < holder_count:
            raise ValidationError(
                f"This role currently has {holder_count} holder(s); "
                f"can't cap it below that."
            )
        role.max_holders = max_holders

    role = governance_role_repository.save(db, role)
    audit_service.log(db, ENTITY_TYPE, role.id, "updated", actor_id, {"name": role.name})
    return role


def delete_role(db: Session, role_id: int, actor_id: int | None) -> None:
    role = _get_role_or_raise(db, role_id)
    if governance_role_repository.has_children(db, role_id):
        raise ConflictError(
            f"'{role.name}' still has roles reporting to it; reassign those first."
        )
    for assignment in governance_role_repository.list_assignments_for_role(db, role_id):
        governance_role_repository.delete_assignment(db, assignment)

    governance_role_repository.delete(db, role)
    audit_service.log(db, ENTITY_TYPE, role_id, "deleted", actor_id, {"name": role.name})


def assign_user(
    db: Session, role_id: int, user_id: int, actor_id: int | None
) -> GovernanceRoleAssignment:
    role = _get_role_or_raise(db, role_id)
    user = _get_user_or_raise(db, user_id)

    if governance_role_repository.get_assignment(db, role_id, user_id) is not None:
        raise ConflictError(f"{user.name} already holds '{role.name}'.")
    if role.max_holders is not None:
        current = governance_role_repository.count_holders(db, role_id)
        if current >= role.max_holders:
            raise ConflictError(
                f"'{role.name}' already has its maximum of {role.max_holders} holder(s); "
                "remove the current holder first."
            )
    # The user's own framing: the Chief AI Governance Officer "will be the
    # admin" -- so this designated role can't land on a non-admin account.
    if role.name == CHIEF_AI_GOVERNANCE_OFFICER and user.role != UserRole.ADMIN:
        raise ValidationError(
            "Chief AI Governance Officer must be an admin account."
        )

    assignment = GovernanceRoleAssignment(
        governance_role_id=role_id, user_id=user_id, assigned_by=actor_id
    )
    assignment = governance_role_repository.create_assignment(db, assignment)
    audit_service.log(
        db, ENTITY_TYPE, role_id, "user_assigned", actor_id,
        {"user_id": user_id, "role_name": role.name},
    )
    return assignment


def unassign_user(db: Session, role_id: int, user_id: int, actor_id: int | None) -> None:
    role = _get_role_or_raise(db, role_id)
    assignment = governance_role_repository.get_assignment(db, role_id, user_id)
    if assignment is None:
        raise NotFoundError("GovernanceRoleAssignment", user_id)

    governance_role_repository.delete_assignment(db, assignment)
    audit_service.log(
        db, ENTITY_TYPE, role_id, "user_unassigned", actor_id,
        {"user_id": user_id, "role_name": role.name},
    )


def list_roles_for_user(db: Session, user_id: int) -> list[GovernanceRole]:
    role_ids = {
        a.governance_role_id
        for a in governance_role_repository.list_assignments_for_user(db, user_id)
    }
    if not role_ids:
        return []
    return [role for role in governance_role_repository.list_all(db) if role.id in role_ids]


def role_names_by_user(db: Session) -> dict[int, list[str]]:
    """Every user's governance role names in one query -- what the user
    directory badges every picker with."""
    roles_by_id = {role.id: role.name for role in governance_role_repository.list_all(db)}
    result: dict[int, list[str]] = {}
    for assignment in governance_role_repository.list_all_assignments(db):
        name = roles_by_id.get(assignment.governance_role_id)
        if name:
            result.setdefault(assignment.user_id, []).append(name)
    return result


def holders_for_role(db: Session, role_id: int) -> list[User]:
    holder_ids = [
        a.user_id for a in governance_role_repository.list_assignments_for_role(db, role_id)
    ]
    return [user for uid in holder_ids if (user := db.get(User, uid)) is not None]
