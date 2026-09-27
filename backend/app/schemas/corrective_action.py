from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.corrective_action import CorrectiveActionStatus
from app.schemas.framework_control import FrameworkControlRead


class CorrectiveActionCreate(BaseModel):
    title: str
    nonconformity_description: str
    root_cause: str | None = None
    action_description: str | None = None
    source_type: str | None = None
    source_id: int | None = None
    # Required here, even though the column stays nullable at rest for later
    # reassignment/clearing -- this is where "assigned responsibilities" and
    # "resolution timelines" are actually enforced.
    assignee_id: int
    due_date: date


class CorrectiveActionUpdate(BaseModel):
    """status may only move between open and in_progress here -- reaching
    pending_verification or closed goes through the dedicated submit/verify
    endpoints instead, which is where the evidence and CAIGO checks live."""

    title: str | None = None
    nonconformity_description: str | None = None
    root_cause: str | None = None
    action_description: str | None = None
    source_type: str | None = None
    source_id: int | None = None
    assignee_id: int | None = None
    due_date: date | None = None
    status: CorrectiveActionStatus | None = None


class CorrectiveActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    nonconformity_description: str
    root_cause: str | None
    action_description: str | None
    source_type: str | None
    source_id: int | None
    assignee_id: int | None
    due_date: date
    status: CorrectiveActionStatus
    overdue: bool
    framework_tags: list[FrameworkControlRead]
    closed_by: int | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
