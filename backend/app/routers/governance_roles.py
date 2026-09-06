from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_manage_users_user
from app.models.governance_role import GovernanceRole
from app.models.user import User
from app.schemas.governance_role import (
    AssignmentInput,
    GovernanceRoleCreate,
    GovernanceRoleRead,
    GovernanceRoleUpdate,
    OrgChartNode,
    RoleHolder,
)
from app.services import governance_role_service

router = APIRouter(prefix="/governance-roles", tags=["governance-roles"])


def _to_read(db: Session, role: GovernanceRole) -> GovernanceRoleRead:
    holders = governance_role_service.holders_for_role(db, role.id)
    return GovernanceRoleRead(
        id=role.id,
        name=role.name,
        responsibilities=role.responsibilities,
        max_holders=role.max_holders,
        parent_role_id=role.parent_role_id,
        holders=[RoleHolder(id=u.id, name=u.name) for u in holders],
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


@router.get("", response_model=list[GovernanceRoleRead])
def list_roles(db: Session = Depends(get_db)) -> list[GovernanceRoleRead]:
    return [_to_read(db, role) for role in governance_role_service.list_roles(db)]


# Declared before /{role_id} so the path param doesn't swallow "org-chart".
@router.get("/org-chart", response_model=list[OrgChartNode])
def get_org_chart(db: Session = Depends(get_db)) -> list[OrgChartNode]:
    nodes = []
    for role in governance_role_service.list_roles(db):
        holders = governance_role_service.holders_for_role(db, role.id)
        nodes.append(
            OrgChartNode(
                id=role.id,
                name=role.name,
                parent_role_id=role.parent_role_id,
                max_holders=role.max_holders,
                holders=[RoleHolder(id=u.id, name=u.name) for u in holders],
            )
        )
    return nodes


@router.post("", response_model=GovernanceRoleRead, status_code=201)
def create_role(
    data: GovernanceRoleCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users_user),
) -> GovernanceRoleRead:
    role = governance_role_service.create_role(
        db, data.name, data.responsibilities, data.parent_role_id, data.max_holders, actor.id
    )
    return _to_read(db, role)


@router.patch("/{role_id}", response_model=GovernanceRoleRead)
def update_role(
    role_id: int,
    data: GovernanceRoleUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users_user),
) -> GovernanceRoleRead:
    fields = data.model_fields_set
    role = governance_role_service.update_role(
        db,
        role_id,
        data.name,
        data.responsibilities,
        data.parent_role_id,
        "parent_role_id" in fields,
        data.max_holders,
        "max_holders" in fields,
        actor.id,
    )
    return _to_read(db, role)


@router.delete("/{role_id}", status_code=204)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users_user),
) -> None:
    governance_role_service.delete_role(db, role_id, actor.id)


@router.post("/{role_id}/assignments", response_model=GovernanceRoleRead, status_code=201)
def assign_user(
    role_id: int,
    data: AssignmentInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users_user),
) -> GovernanceRoleRead:
    governance_role_service.assign_user(db, role_id, data.user_id, actor.id)
    return _to_read(db, governance_role_service.get_role(db, role_id))


@router.delete("/{role_id}/assignments/{user_id}", response_model=GovernanceRoleRead)
def unassign_user(
    role_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users_user),
) -> GovernanceRoleRead:
    governance_role_service.unassign_user(db, role_id, user_id, actor.id)
    return _to_read(db, governance_role_service.get_role(db, role_id))
