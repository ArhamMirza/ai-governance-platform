from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.governance_role import GovernanceRole
from app.models.governance_role_assignment import GovernanceRoleAssignment
from app.models.governance_role_delegation import GovernanceRoleDelegation


def list_all(db: Session) -> list[GovernanceRole]:
    return list(db.scalars(select(GovernanceRole).order_by(GovernanceRole.id)))


def get(db: Session, role_id: int) -> GovernanceRole | None:
    return db.get(GovernanceRole, role_id)


def get_by_name(db: Session, name: str) -> GovernanceRole | None:
    return db.scalar(select(GovernanceRole).where(GovernanceRole.name == name))


def create(db: Session, role: GovernanceRole) -> GovernanceRole:
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def save(db: Session, role: GovernanceRole) -> GovernanceRole:
    db.commit()
    db.refresh(role)
    return role


def delete(db: Session, role: GovernanceRole) -> None:
    db.delete(role)
    db.commit()


def has_children(db: Session, role_id: int) -> bool:
    return (
        db.scalar(select(GovernanceRole.id).where(GovernanceRole.parent_role_id == role_id))
        is not None
    )


def list_assignments_for_role(db: Session, role_id: int) -> list[GovernanceRoleAssignment]:
    return list(
        db.scalars(
            select(GovernanceRoleAssignment)
            .where(GovernanceRoleAssignment.governance_role_id == role_id)
            .order_by(GovernanceRoleAssignment.assigned_at)
        )
    )


def list_assignments_for_user(db: Session, user_id: int) -> list[GovernanceRoleAssignment]:
    return list(
        db.scalars(
            select(GovernanceRoleAssignment).where(GovernanceRoleAssignment.user_id == user_id)
        )
    )


def list_all_assignments(db: Session) -> list[GovernanceRoleAssignment]:
    """Every assignment across every role -- used to badge a whole user
    directory in one query instead of one per user."""
    return list(db.scalars(select(GovernanceRoleAssignment)))


def get_assignment(
    db: Session, role_id: int, user_id: int
) -> GovernanceRoleAssignment | None:
    return db.scalar(
        select(GovernanceRoleAssignment).where(
            GovernanceRoleAssignment.governance_role_id == role_id,
            GovernanceRoleAssignment.user_id == user_id,
        )
    )


def count_holders(db: Session, role_id: int) -> int:
    return len(list_assignments_for_role(db, role_id))


def create_assignment_within_cap(
    db: Session, assignment: GovernanceRoleAssignment, max_holders: int | None
) -> bool:
    """Insert, count, and commit as one transaction; report whether the row
    survived. False means the role was already full, and nothing was written.

    "At most N holders" is not something a unique constraint can express, so
    the only way to be sure is to count with the row already in place. That
    has to happen before the commit, not after: a simultaneous assignment
    that counts after committing can run its count before the other insert
    lands, and then both callers see room. Counting inside the transaction
    leaves no such gap -- the insert holds the write lock, so the other
    request is either already visible or still waiting for it."""
    db.add(assignment)
    db.flush()
    if max_holders is not None:
        held = db.scalar(
            select(func.count())
            .select_from(GovernanceRoleAssignment)
            .where(
                GovernanceRoleAssignment.governance_role_id
                == assignment.governance_role_id
            )
        )
        if held > max_holders:
            db.rollback()
            return False
    db.commit()
    db.refresh(assignment)
    return True


def delete_assignment(db: Session, assignment: GovernanceRoleAssignment) -> None:
    db.delete(assignment)
    db.commit()


def get_active_delegation(
    db: Session, role_id: int, now: datetime
) -> GovernanceRoleDelegation | None:
    return db.scalar(
        select(GovernanceRoleDelegation).where(
            GovernanceRoleDelegation.governance_role_id == role_id,
            GovernanceRoleDelegation.revoked_at.is_(None),
            GovernanceRoleDelegation.starts_at <= now,
            GovernanceRoleDelegation.ends_at > now,
        )
    )


def list_unrevoked_delegations(
    db: Session, role_id: int
) -> list[GovernanceRoleDelegation]:
    """Every delegation for the role that hasn't been revoked -- including
    ones whose window has already closed, which get_active_delegation
    excludes. delegate_caigo revokes all of them before creating the next,
    so "unrevoked" means exactly one standing delegation (see the unique
    index on GovernanceRoleDelegation)."""
    return list(
        db.scalars(
            select(GovernanceRoleDelegation).where(
                GovernanceRoleDelegation.governance_role_id == role_id,
                GovernanceRoleDelegation.revoked_at.is_(None),
            )
        )
    )


def create_delegation(
    db: Session, delegation: GovernanceRoleDelegation
) -> GovernanceRoleDelegation:
    db.add(delegation)
    db.commit()
    db.refresh(delegation)
    return delegation


def save_delegation(
    db: Session, delegation: GovernanceRoleDelegation
) -> GovernanceRoleDelegation:
    db.commit()
    db.refresh(delegation)
    return delegation
