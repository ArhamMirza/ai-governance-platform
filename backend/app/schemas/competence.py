from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.framework_control import FrameworkControlRead

CompetenceStatus = Literal["current", "expired", "missing"]


class CompetenceRequirementCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    governance_role_id: int | None = None
    refresh_interval_months: int | None = Field(default=None, ge=1)


class CompetenceRequirementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    governance_role_id: int | None = None
    refresh_interval_months: int | None = Field(default=None, ge=1)


class CompetenceRecordCreate(BaseModel):
    user_id: int
    completed_on: date
    notes: str | None = None


class CompetenceRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requirement_id: int
    user_id: int
    completed_on: date
    notes: str | None
    recorded_by: int | None
    created_at: datetime


class PersonCompetence(BaseModel):
    """One required person's standing against one requirement."""

    user_id: int
    status: CompetenceStatus
    last_completed_on: date | None
    next_due: date | None


class CompetenceRequirementSummary(BaseModel):
    id: int
    title: str
    description: str | None
    governance_role_id: int | None
    refresh_interval_months: int | None
    required_count: int
    current_count: int
    gap_count: int
    created_at: datetime
    updated_at: datetime


class CompetenceRequirementRead(CompetenceRequirementSummary):
    people: list[PersonCompetence]
    records: list[CompetenceRecordRead]
    framework_tags: list[FrameworkControlRead]
