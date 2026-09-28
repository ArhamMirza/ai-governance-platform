from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.framework_control import FrameworkControlRead


class ManagementReviewSettingsUpdate(BaseModel):
    interval_months: int | None = None
    start_date: date | None = None

    @model_validator(mode="after")
    def _interval_requires_start_date(self) -> "ManagementReviewSettingsUpdate":
        if self.interval_months is not None and self.start_date is None:
            raise ValueError("start_date is required once a review interval is configured.")
        return self


class ManagementReviewSettingsRead(BaseModel):
    interval_months: int | None
    start_date: date | None
    next_due_date: date | None
    overdue: bool
    framework_tags: list[FrameworkControlRead]
    updated_at: datetime | None


class ManagementReviewMeetingCreate(BaseModel):
    meeting_date: date
    chaired_by: int | None = None
    attendees: str | None = None
    previous_actions_status: str | None = None
    context_changes: str | None = None
    performance_summary: str | None = None
    stakeholder_feedback: str | None = None
    resource_adequacy: str | None = None
    improvement_opportunities: str | None = None
    decisions_and_actions: str | None = None


class ManagementReviewMeetingUpdate(BaseModel):
    meeting_date: date | None = None
    chaired_by: int | None = None
    attendees: str | None = None
    previous_actions_status: str | None = None
    context_changes: str | None = None
    performance_summary: str | None = None
    stakeholder_feedback: str | None = None
    resource_adequacy: str | None = None
    improvement_opportunities: str | None = None
    decisions_and_actions: str | None = None


class ManagementReviewMeetingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_date: date
    chaired_by: int | None
    attendees: str | None
    previous_actions_status: str | None
    context_changes: str | None
    performance_summary: str | None
    stakeholder_feedback: str | None
    resource_adequacy: str | None
    improvement_opportunities: str | None
    decisions_and_actions: str | None
    framework_tags: list[FrameworkControlRead]
    created_at: datetime
    updated_at: datetime
