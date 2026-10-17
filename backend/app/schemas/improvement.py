from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.improvement_tracking import ImprovementState
from app.models.improvement import ImprovementSource, ImprovementStatus
from app.schemas.framework_control import FrameworkControlRead

# The records an improvement can point back to.
ImprovementSourceType = Literal[
    "AuditFinding",
    "ManagementReviewMeeting",
    "Concern",
    "AIIncident",
    "CorrectiveAction",
    "AIObjective",
]


class ImprovementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    expected_benefit: str | None = None
    source: ImprovementSource = ImprovementSource.OTHER
    # Both set, or both None -- see improvement_service.create_improvement.
    source_type: ImprovementSourceType | None = None
    source_id: int | None = None
    owner_id: int | None = None
    # Defaults to today (improvement_service.create_improvement).
    raised_on: date | None = None
    target_date: date


class ImprovementUpdate(BaseModel):
    """The source isn't editable: it's what the improvement arose from."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    expected_benefit: str | None = None
    owner_id: int | None = None
    raised_on: date | None = None
    target_date: date | None = None


class ImprovementStatusUpdate(BaseModel):
    """Where the person is moving it. `implement` needs the outcome and
    `decline` a reason; `reopen` puts a closed one back to where it was."""

    action: Literal["accept", "implement", "decline", "reopen"]
    note: str | None = None


class ImprovementStandingRead(BaseModel):
    """Computed, never stored -- see app.core.improvement_tracking."""

    state: ImprovementState
    overdue: bool


class ImprovementRead(BaseModel):
    id: int
    title: str
    description: str | None
    expected_benefit: str | None
    source: ImprovementSource
    source_type: str | None
    source_id: int | None
    # What the source record is called, or None once it no longer exists.
    source_label: str | None
    owner_id: int | None
    raised_on: date
    target_date: date
    status: ImprovementStatus
    decided_on: date | None
    closed_on: date | None
    outcome: str | None
    decline_reason: str | None
    change_id: int | None
    standing: ImprovementStandingRead
    framework_tags: list[FrameworkControlRead]
    created_at: datetime
    updated_at: datetime


class ImprovementAsOfRead(BaseModel):
    """One improvement as it stood on a past date -- for a management review
    meeting, showing what was known when it met."""

    id: int
    title: str
    source: ImprovementSource
    owner_id: int | None
    target_date: date
    standing: ImprovementStandingRead
