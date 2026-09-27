from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.audit_finding import AuditFindingType
from app.models.audit_program import AuditProgramStatus, AuditScheduleType
from app.models.internal_audit import InternalAuditStatus
from app.schemas.framework_control import FrameworkControlRead


class AuditProgramCreate(BaseModel):
    title: str
    description: str | None = None
    schedule_type: AuditScheduleType = AuditScheduleType.INTERVAL
    interval_months: int | None = None
    start_date: date | None = None
    owner_id: int | None = None

    @model_validator(mode="after")
    def _interval_requires_months(self) -> "AuditProgramCreate":
        if self.schedule_type == AuditScheduleType.INTERVAL and not self.interval_months:
            raise ValueError("interval_months is required for an interval-based audit program.")
        if self.schedule_type == AuditScheduleType.AD_HOC:
            self.interval_months = None
        return self


class AuditProgramUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    schedule_type: AuditScheduleType | None = None
    interval_months: int | None = None
    start_date: date | None = None
    owner_id: int | None = None
    status: AuditProgramStatus | None = None


class AuditProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    schedule_type: AuditScheduleType
    interval_months: int | None
    start_date: date | None
    owner_id: int | None
    status: AuditProgramStatus
    next_due_date: date | None
    overdue: bool
    framework_tags: list[FrameworkControlRead]
    created_at: datetime
    updated_at: datetime


class InternalAuditCreate(BaseModel):
    title: str
    planned_date: date
    auditor_id: int | None = None
    scope: str | None = None


class InternalAuditUpdate(BaseModel):
    title: str | None = None
    planned_date: date | None = None
    auditor_id: int | None = None
    scope: str | None = None
    conclusion: str | None = None
    status: InternalAuditStatus | None = None


class InternalAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    audit_program_id: int
    title: str
    planned_date: date
    conducted_date: date | None
    auditor_id: int | None
    scope: str | None
    conclusion: str | None
    status: InternalAuditStatus
    overdue: bool
    created_at: datetime
    updated_at: datetime


class AuditFindingCreate(BaseModel):
    description: str
    finding_type: AuditFindingType = AuditFindingType.OBSERVATION


class AuditFindingUpdate(BaseModel):
    description: str | None = None
    finding_type: AuditFindingType | None = None


class AuditFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    internal_audit_id: int
    description: str
    finding_type: AuditFindingType
    corrective_action_ids: list[int]
    created_at: datetime
    updated_at: datetime
