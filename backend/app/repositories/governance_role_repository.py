from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.governance_role import GovernanceRole
from app.models.governance_role_assignment import GovernanceRoleAssignment


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


def create_assignment(
    db: Session, assignment: GovernanceRoleAssignment
) -> GovernanceRoleAssignment:
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def delete_assignment(db: Session, assignment: GovernanceRoleAssignment) -> None:
    db.delete(assignment)
    db.commit()
