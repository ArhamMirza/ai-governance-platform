from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.policy import PolicyStatus


class PolicyCreate(BaseModel):
    title: str
    description: str | None = None
    owner_id: int | None = None
    effective_date: date | None = None


class PolicyUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    owner_id: int | None = None
    effective_date: date | None = None


class PolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: PolicyStatus
    version: int
    owner_id: int | None
    effective_date: date | None
    next_review_date: date | None
    created_at: datetime
    updated_at: datetime


class PolicyHistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action: str
    actor_id: int | None
    timestamp: datetime
    diff: dict | None
