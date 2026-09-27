"""Organizational accountability, separate from (but partly linked to) the
technical admin/contributor/viewer permission a user holds -- see
CHIEF_AI_GOVERNANCE_OFFICER's admin-only rule below for where they connect.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.concurrency import conflict_on_duplicate
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.models.governance_role import GovernanceRole
from app.models.governance_role_assignment import GovernanceRoleAssignment
from app.models.governance_role_delegation import GovernanceRoleDelegation
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
        # CAIGO is looked up by this exact name throughout the app --
        # is_caigo, require_caigo, delegate_caigo, and the frontend's
        # useCanApprove all key off the literal "Chief AI Governance
        # Officer" string rather than this role's id. Renaming it would
        # silently break every one of those lookups (no one could approve
        # anything CAIGO-gated, delegation would look up a role that no
        # longer matches), so the name itself is not editable.
        if role.name == CHIEF_AI_GOVERNANCE_OFFICER:
            raise ValidationError(
                "Chief AI Governance Officer can't be renamed -- too much of the "
                "approval system identifies this role by that exact name."
            )
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
    # Same reasoning as the rename guard in update_role: is_caigo, require_caigo
    # and delegate_caigo all find this role by its exact name. Deleting it makes
    # every one of those lookups fail, so nothing CAIGO-gated could be approved
    # anywhere in the app -- recoverable only by recreating a role with exactly
    # this name, which is not something anyone should have to guess.
    if role.name == CHIEF_AI_GOVERNANCE_OFFICER:
        raise ConflictError(
            "Chief AI Governance Officer can't be deleted -- every approval in "
            "the app is gated on this role. Reassign the holder instead."
        )
    if governance_role_repository.has_children(db, role_id):
        raise ConflictError(
            f"'{role.name}' still has roles reporting to it; reassign those first."
        )
    for assignment in governance_role_repository.list_assignments_for_role(db, role_id):
        governance_role_repository.delete_assignment(db, assignment)

    governance_role_repository.delete(db, role)
    audit_service.log(db, ENTITY_TYPE, role_id, "deleted", actor_id, {"name": role.name})


def _at_capacity_message(role: GovernanceRole) -> str:
    return (
        f"'{role.name}' already has its maximum of {role.max_holders} holder(s); "
        "remove the current holder first."
    )


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
            raise ConflictError(_at_capacity_message(role))
    # The user's own framing: the Chief AI Governance Officer "will be the
    # admin" -- so this designated role can't land on a non-admin account.
    if role.name == CHIEF_AI_GOVERNANCE_OFFICER and user.role != UserRole.ADMIN:
        raise ValidationError(
            "Chief AI Governance Officer must be an admin account."
        )

    assignment = GovernanceRoleAssignment(
        governance_role_id=role_id, user_id=user_id, assigned_by=actor_id
    )
    # Both checks above ran in transactions of their own, so a simultaneous
    # assignment can pass them too. The unique constraint settles the
    # duplicate; the cap is settled by counting with the row already in
    # place, which is the repository's job because it has to happen before
    # the commit.
    with conflict_on_duplicate(db, f"{user.name} already holds '{role.name}'."):
        assigned = governance_role_repository.create_assignment_within_cap(
            db, assignment, role.max_holders
        )
    if not assigned:
        raise ConflictError(_at_capacity_message(role))
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
    # Deactivating this same person is still allowed with only a warning
    # (see user_service.get_accountabilities) -- access can't wait on
    # paperwork. But removing them from the role itself is a deliberate,
    # single-purpose click with nothing else it could be for, and unlike
    # deactivation it carries no warning today -- so unlike deactivation,
    # this one is refused outright rather than merely surfaced first.
    if role.name == CHIEF_AI_GOVERNANCE_OFFICER and not has_other_eligible_approver(
        db, user_id
    ):
        holder = _get_user_or_raise(db, user_id)
        raise ConflictError(
            f"{holder.name} is the only person who could approve anything "
            "CAIGO-gated right now -- removing them would leave nothing in "
            "the app able to. Set a backup approver, or assign someone else "
            "to this role first."
        )

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

    # An active delegate stands in for CAIGO -- badge them the same as a
    # real holder so useCanApprove (which reads this badge list, not a live
    # is_caigo call) shows the Approve button for them too.
    delegate = active_caigo_delegate(db)
    if delegate is not None:
        badges = result.setdefault(delegate.id, [])
        if CHIEF_AI_GOVERNANCE_OFFICER not in badges:
            badges.append(CHIEF_AI_GOVERNANCE_OFFICER)
    return result


def vacant_roles(db: Session) -> list[GovernanceRole]:
    """Roles with zero holders -- bulk list_all + list_all_assignments (both
    already exist) rather than count_holders per role, to avoid an N+1
    query across every role."""
    held_role_ids = {
        a.governance_role_id for a in governance_role_repository.list_all_assignments(db)
    }
    return [
        role for role in governance_role_repository.list_all(db) if role.id not in held_role_ids
    ]


def holders_for_role(db: Session, role_id: int) -> list[User]:
    holder_ids = [
        a.user_id for a in governance_role_repository.list_assignments_for_role(db, role_id)
    ]
    return [user for uid in holder_ids if (user := db.get(User, uid)) is not None]


def is_caigo(db: Session, user_id: int) -> bool:
    role = governance_role_repository.get_by_name(db, CHIEF_AI_GOVERNANCE_OFFICER)
    if role is None:
        return False
    if any(user.id == user_id for user in holders_for_role(db, role.id)):
        return True
    delegate = active_caigo_delegate(db)
    return delegate is not None and delegate.id == user_id


def require_caigo(db: Session, user_id: int | None) -> None:
    """No real actor (seed script / direct service call) means nothing to
    enforce -- mirrors audit_service.require_different_approver's same
    no-op-on-None behavior."""
    if user_id is None:
        return
    if not is_caigo(db, user_id):
        raise AuthorizationError(
            "Only the Chief AI Governance Officer can approve this."
        )


def has_other_eligible_approver(db: Session, excluding_user_id: int) -> bool:
    """Whether anyone besides excluding_user_id could satisfy require_caigo --
    another CAIGO role holder, or an active delegate who isn't this same
    person. Used to catch, before it happens, a submission that would leave
    a record with no one left who can approve it."""
    role = governance_role_repository.get_by_name(db, CHIEF_AI_GOVERNANCE_OFFICER)
    if role is not None and any(
        user.id != excluding_user_id for user in holders_for_role(db, role.id)
    ):
        return True
    delegate = active_caigo_delegate(db)
    return delegate is not None and delegate.id != excluding_user_id


def require_a_possible_approver(db: Session, actor_id: int | None) -> None:
    """Refuses a submission that would strand the record: the actor is the
    CAIGO (or standing in as their delegate), and require_different_approver
    will later refuse to let this same person approve their own submission --
    if no one else could stand in either, the record would sit in review
    with nobody able to move it. The fix is a backup approver, so the error
    says so; it is not a general ban on the CAIGO authoring documents, only
    on them being the one who also submits it with no stand-in available.

    No real actor is nothing to enforce, matching require_caigo and
    audit_service.require_different_approver's own no-op-on-None rule."""
    if actor_id is None:
        return
    if not is_caigo(db, actor_id):
        return
    if has_other_eligible_approver(db, actor_id):
        return
    raise ValidationError(
        "You are the only person who can approve this, and the same person "
        "can't both submit and approve it. Set a backup approver for the "
        "Chief AI Governance Officer role first, or have someone else "
        "submit this for review."
    )


def get_caigo_delegation(db: Session) -> GovernanceRoleDelegation | None:
    role = governance_role_repository.get_by_name(db, CHIEF_AI_GOVERNANCE_OFFICER)
    if role is None:
        return None
    return governance_role_repository.get_active_delegation(db, role.id, datetime.now(UTC))


def active_caigo_delegate(db: Session) -> User | None:
    delegation = get_caigo_delegation(db)
    if delegation is None:
        return None
    return db.get(User, delegation.delegate_user_id)


def delegate_caigo(
    db: Session, delegate_user_id: int, ends_at: datetime, actor_id: int | None
) -> GovernanceRoleDelegation:
    role = governance_role_repository.get_by_name(db, CHIEF_AI_GOVERNANCE_OFFICER)
    if role is None:
        raise NotFoundError("GovernanceRole", 0)
    delegate = _get_user_or_raise(db, delegate_user_id)
    # Same rule assign_user already enforces for CAIGO itself -- a backup
    # approver for this seat must be an admin account too.
    if delegate.role != UserRole.ADMIN:
        raise ValidationError("The backup approver must be an admin account.")

    now = datetime.now(UTC)
    if ends_at <= now:
        raise ValidationError("The delegation's end time must be in the future.")

    # Every unrevoked delegation, not just the one active right now: a
    # delegation whose window has closed is spent, but leaving it unrevoked
    # would count as a second standing delegation under the unique index and
    # block every delegation after it.
    for existing in governance_role_repository.list_unrevoked_delegations(db, role.id):
        existing.revoked_at = now
        governance_role_repository.save_delegation(db, existing)

    delegation = GovernanceRoleDelegation(
        governance_role_id=role.id,
        delegate_user_id=delegate_user_id,
        starts_at=now,
        ends_at=ends_at,
        created_by=actor_id,
    )
    # Two simultaneous delegations each revoke what they found and insert,
    # which would leave the role with two stand-ins; the index stops the
    # second, and whoever lost can name their delegate again.
    with conflict_on_duplicate(
        db,
        "Someone else set up a backup approver at the same moment. "
        "Check who holds it now before delegating again.",
    ):
        delegation = governance_role_repository.create_delegation(db, delegation)
    audit_service.log(
        db, ENTITY_TYPE, role.id, "caigo_delegated", actor_id,
        {"delegate_user_id": delegate_user_id, "ends_at": ends_at.isoformat()},
    )
    return delegation


def revoke_caigo_delegation(db: Session, actor_id: int | None) -> None:
    role = governance_role_repository.get_by_name(db, CHIEF_AI_GOVERNANCE_OFFICER)
    if role is None:
        raise NotFoundError("GovernanceRole", 0)
    active = governance_role_repository.get_active_delegation(db, role.id, datetime.now(UTC))
    if active is None:
        raise ValidationError("There is no active CAIGO delegation to revoke.")

    active.revoked_at = datetime.now(UTC)
    governance_role_repository.save_delegation(db, active)
    audit_service.log(db, ENTITY_TYPE, role.id, "caigo_delegation_revoked", actor_id, {})
