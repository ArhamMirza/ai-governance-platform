from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.communication import CommunicationDirection, CommunicationStatus
from app.schemas.framework_control import FrameworkControlRead


class CommunicationCreate(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    audience: str = Field(min_length=1, max_length=300)
    direction: CommunicationDirection = CommunicationDirection.INTERNAL
    method: str | None = Field(default=None, max_length=200)
    responsible_id: int | None = None
    notes: str | None = None
    interval_months: int | None = Field(default=None, ge=1)
    first_due: date | None = None


class CommunicationUpdate(BaseModel):
    topic: str | None = Field(default=None, min_length=1, max_length=200)
    audience: str | None = Field(default=None, min_length=1, max_length=300)
    direction: CommunicationDirection | None = None
    method: str | None = Field(default=None, max_length=200)
    responsible_id: int | None = None
    notes: str | None = None
    status: CommunicationStatus | None = None
    interval_months: int | None = Field(default=None, ge=1)
    first_due: date | None = None


class CommunicationRecordCreate(BaseModel):
    communicated_on: date
    summary: str | None = None


class CommunicationRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    communication_id: int
    communicated_on: date
    summary: str | None
    recorded_by: int | None
    created_at: datetime


class CommunicationRead(BaseModel):
    id: int
    topic: str
    audience: str
    direction: CommunicationDirection
    method: str | None
    responsible_id: int | None
    notes: str | None
    status: CommunicationStatus
    interval_months: int | None
    first_due: date | None
    # Computed, never stored -- see app.core.communication_schedule.
    last_communicated_on: date | None
    next_due: date | None
    overdue: bool
    framework_tags: list[FrameworkControlRead]
    created_at: datetime
    updated_at: datetime


class CommunicationDetailRead(CommunicationRead):
    records: list[CommunicationRecordRead]
