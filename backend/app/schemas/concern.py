from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.models.concern import ConcernCategory, ConcernChannel, ConcernOutcome, ConcernStatus
from app.schemas.framework_control import FrameworkControlRead

# ---------- what an employee sends and sees ----------


class ConcernSubmit(BaseModel):
    category: ConcernCategory = ConcernCategory.OTHER
    description: str = Field(min_length=10, max_length=5000)
    ai_system_row_id: int | None = None
    # When they aren't sure which system.
    system_note: str | None = Field(default=None, max_length=300)
    # When true nothing identifying is stored -- see Concern.
    anonymous: bool = False


class ReporterConcernRead(BaseModel):
    """A concern as its own reporter sees it: what they said, where it stands
    and what the handler replied. Never internal notes or the handler."""

    id: int
    category: ConcernCategory
    description: str
    received_on: date
    status: ConcernStatus
    acknowledged_on: date | None
    closed_on: date | None
    outcome: ConcernOutcome | None
    reply_to_reporter: str | None
    is_anonymous: bool


class ConcernSubmitted(BaseModel):
    """Returned once, on submission. The tracking code is the only way back
    to an anonymous concern and isn't stored, so it can't be shown again."""

    tracking_code: str
    concern: ReporterConcernRead


class ConcernLookup(BaseModel):
    tracking_code: str = Field(min_length=1, max_length=60)


class StaffAISystem(BaseModel):
    id: int
    name: str


class ConcernsProcess(BaseModel):
    process_description: str | None
    acknowledge_within_days: int


# ---------- what a handler sends and sees ----------


class ConcernLog(BaseModel):
    """A concern raised another way -- a call, an email, in person -- recorded
    by a handler."""

    category: ConcernCategory = ConcernCategory.OTHER
    description: str = Field(min_length=1, max_length=5000)
    channel: ConcernChannel
    received_on: date | None = None
    ai_system_row_id: int | None = None
    system_note: str | None = Field(default=None, max_length=300)
    anonymous: bool = False
    reporter_note: str | None = None


class ConcernUpdate(BaseModel):
    category: ConcernCategory | None = None
    ai_system_row_id: int | None = None
    system_note: str | None = Field(default=None, max_length=300)
    handler_id: int | None = None
    internal_notes: str | None = None
    reply_to_reporter: str | None = None


class ConcernStatusUpdate(BaseModel):
    action: Literal["acknowledge", "resolve", "dismiss", "reopen"]
    # Required to resolve.
    outcome: ConcernOutcome | None = None
    # Required to dismiss -- why it isn't being taken further.
    note: str | None = None


class RaiseCorrectiveAction(BaseModel):
    title: str = Field(min_length=1)
    action_description: str | None = None
    assignee_id: int
    due_date: date


class ConcernRead(BaseModel):
    id: int
    category: ConcernCategory
    description: str
    ai_system_row_id: int | None
    system_note: str | None
    channel: ConcernChannel
    received_on: date
    is_anonymous: bool
    reporter_id: int | None
    # Looked up from reporter_id; None for an anonymous concern.
    reporter_name: str | None
    reporter_note: str | None
    status: ConcernStatus
    handler_id: int | None
    acknowledged_on: date | None
    closed_on: date | None
    outcome: ConcernOutcome | None
    internal_notes: str | None
    closure_note: str | None
    reply_to_reporter: str | None
    incident_id: int | None
    # Computed, never stored -- see app.core.concern_tracking.
    acknowledge_by: date
    awaiting_triage: bool


class ConcernSettingsRead(BaseModel):
    id: int
    process_description: str | None
    acknowledge_within_days: int
    framework_tags: list[FrameworkControlRead]


class ConcernSettingsUpdate(BaseModel):
    process_description: str | None = None
    acknowledge_within_days: int | None = Field(default=None, ge=1, le=90)


class ConcernAccess(BaseModel):
    can_handle: bool
