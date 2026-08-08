from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.policy import PolicyStatus


class PolicyCreate(BaseModel):
    title: str
    description: str | None = None
    content: str = ""
    owner_id: int | None = None
    effective_date: date | None = None


class PolicyUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    content: str | None = None
    effective_date: date | None = None
    change_note: str | None = None


class PolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: PolicyStatus
    version: int
    owner_id: int | None
    content: str
    effective_date: date | None
    created_at: datetime
    updated_at: datetime


class PolicyVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_id: int
    version_no: int
    content: str
    changed_by: int | None
    changed_at: datetime
    change_note: str | None
