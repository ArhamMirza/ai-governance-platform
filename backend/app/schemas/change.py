from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.change_tracking import ChangeState
from app.models.management_system_change import ChangeStatus, ChangeType
from app.schemas.framework_control import FrameworkControlRead


class ChangeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    change_type: ChangeType = ChangeType.OTHER
    reason: str | None = None
    consequences: str | None = None
    resources_needed: str | None = None
    owner_id: int | None = None
    # Defaults to today (change_service.create_change).
    raised_on: date | None = None
    planned_date: date


class ChangeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    change_type: ChangeType | None = None
    reason: str | None = None
    consequences: str | None = None
    resources_needed: str | None = None
    owner_id: int | None = None
    raised_on: date | None = None
    planned_date: date | None = None


class ChangeStatusUpdate(BaseModel):
    """Where the person is moving it. `reopen` puts a closed change back to
    where it was before it closed."""

    action: Literal["start", "implement", "cancel", "reopen"]
    note: str | None = None


class ChangeAISystemsUpdate(BaseModel):
    ai_system_row_ids: list[int]


class ChangeStandingRead(BaseModel):
    """Computed, never stored -- see app.core.change_tracking."""

    state: ChangeState
    overdue: bool


class ChangeRead(BaseModel):
    id: int
    title: str
    description: str | None
    change_type: ChangeType
    reason: str | None
    consequences: str | None
    resources_needed: str | None
    owner_id: int | None
    raised_on: date
    planned_date: date
    status: ChangeStatus
    started_on: date | None
    closed_on: date | None
    closure_note: str | None
    ai_system_row_ids: list[int]
    standing: ChangeStandingRead
    framework_tags: list[FrameworkControlRead]
    created_at: datetime
    updated_at: datetime


class ChangeAsOfRead(BaseModel):
    """One change as it stood on a past date -- for a management review
    meeting, showing what was known when it met."""

    id: int
    title: str
    change_type: ChangeType
    owner_id: int | None
    planned_date: date
    standing: ChangeStandingRead
