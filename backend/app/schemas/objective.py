from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.objective_tracking import ObjectiveState
from app.models.ai_objective import ObjectiveKind, ObjectiveStatus, TargetDirection
from app.schemas.framework_control import FrameworkControlRead


class ObjectiveCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    kind: ObjectiveKind = ObjectiveKind.MEASURED
    owner_id: int | None = None
    policy_id: int | None = None
    # Defaults to today (objective_service.create_objective).
    established_on: date | None = None
    target_date: date | None = None
    planned_actions: str | None = None
    resources: str | None = None
    evaluation_method: str | None = None
    metric_name: str | None = Field(default=None, max_length=200)
    unit: str | None = Field(default=None, max_length=30)
    direction: TargetDirection | None = None
    target_value: float | None = None
    baseline_value: float | None = None
    measurement_interval_months: int | None = Field(default=None, ge=1)
    first_measurement_due: date | None = None


class ObjectiveUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    kind: ObjectiveKind | None = None
    owner_id: int | None = None
    policy_id: int | None = None
    established_on: date | None = None
    target_date: date | None = None
    planned_actions: str | None = None
    resources: str | None = None
    evaluation_method: str | None = None
    metric_name: str | None = Field(default=None, max_length=200)
    unit: str | None = Field(default=None, max_length=30)
    direction: TargetDirection | None = None
    target_value: float | None = None
    baseline_value: float | None = None
    measurement_interval_months: int | None = Field(default=None, ge=1)
    first_measurement_due: date | None = None


class ObjectiveClose(BaseModel):
    status: ObjectiveStatus
    closure_note: str | None = None


class ObjectiveAISystemsUpdate(BaseModel):
    ai_system_row_ids: list[int]


class MeasurementCreate(BaseModel):
    measured_on: date
    value: float
    note: str | None = None


class MeasurementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    objective_id: int
    measured_on: date
    value: float
    note: str | None
    recorded_by: int | None
    created_at: datetime


class ObjectiveStandingRead(BaseModel):
    """Computed, never stored -- see app.core.objective_tracking."""

    state: ObjectiveState
    latest_value: float | None
    latest_on: date | None
    next_measurement_due: date | None
    measurement_overdue: bool


class ObjectiveRead(BaseModel):
    id: int
    title: str
    description: str | None
    kind: ObjectiveKind
    owner_id: int | None
    policy_id: int | None
    established_on: date
    target_date: date | None
    planned_actions: str | None
    resources: str | None
    evaluation_method: str | None
    metric_name: str | None
    unit: str | None
    direction: TargetDirection | None
    target_value: float | None
    baseline_value: float | None
    measurement_interval_months: int | None
    first_measurement_due: date | None
    status: ObjectiveStatus
    closed_on: date | None
    closure_note: str | None
    ai_system_row_ids: list[int]
    standing: ObjectiveStandingRead
    framework_tags: list[FrameworkControlRead]
    created_at: datetime
    updated_at: datetime


class ObjectiveDetailRead(ObjectiveRead):
    measurements: list[MeasurementRead]


class ObjectiveAsOfRead(BaseModel):
    """One objective's standing as of a past date -- for a management
    review meeting, showing what was known when it met."""

    id: int
    title: str
    kind: ObjectiveKind
    metric_name: str | None
    unit: str | None
    direction: TargetDirection | None
    target_value: float | None
    target_date: date | None
    owner_id: int | None
    standing: ObjectiveStandingRead
