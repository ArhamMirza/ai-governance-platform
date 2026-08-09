from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.procedure import ProcedureStatus


class ProcedureCreate(BaseModel):
    title: str
    description: str | None = None
    owner_id: int | None = None
    policy_id: int | None = None
    effective_date: date | None = None


class ProcedureUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    policy_id: int | None = None
    effective_date: date | None = None


class ProcedureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: ProcedureStatus
    version: int
    owner_id: int | None
    policy_id: int | None
    effective_date: date | None
    created_at: datetime
    updated_at: datetime


class ProcedureHistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action: str
    actor_id: int | None
    timestamp: datetime
    diff: dict | None
