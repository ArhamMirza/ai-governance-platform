from datetime import datetime

from pydantic import BaseModel


class GovernanceRoleCreate(BaseModel):
    name: str
    responsibilities: str
    parent_role_id: int | None = None
    max_holders: int | None = None


class GovernanceRoleUpdate(BaseModel):
    name: str | None = None
    responsibilities: str | None = None
    parent_role_id: int | None = None
    max_holders: int | None = None


class AssignmentInput(BaseModel):
    user_id: int


class RoleHolder(BaseModel):
    id: int
    name: str


class GovernanceRoleRead(BaseModel):
    id: int
    name: str
    responsibilities: str
    max_holders: int | None
    parent_role_id: int | None
    holders: list[RoleHolder]
    created_at: datetime
    updated_at: datetime


class OrgChartNode(BaseModel):
    id: int
    name: str
    parent_role_id: int | None
    max_holders: int | None
    holders: list[RoleHolder]


class CaigoDelegationCreate(BaseModel):
    delegate_user_id: int
    ends_at: datetime


class CaigoDelegationRead(BaseModel):
    id: int
    delegate_user_id: int
    delegate_name: str
    starts_at: datetime
    ends_at: datetime
