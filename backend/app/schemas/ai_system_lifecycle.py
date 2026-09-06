from datetime import date, datetime

from pydantic import BaseModel


class GateRequirementRead(BaseModel):
    key: str
    label: str
    satisfied: bool
    detail: str


class AISystemLifecycleRead(BaseModel):
    ai_system_row_id: int
    current_stage: str
    current_stage_label: str
    next_stage: str | None
    next_stage_label: str | None
    entered_stage_at: datetime

    owner_id: int | None

    deployment_environment: str | None
    deployment_version: str | None
    deployed_at: date | None
    deployment_approved_by: int | None
    deployment_approved_at: datetime | None

    monitoring_owner_id: int | None
    incident_escalation_path: str | None

    retirement_reason: str | None
    retirement_approved_by: int | None
    retirement_approved_at: datetime | None
    retired_at: date | None
    retention_until: date | None
    archived_at: datetime | None
    is_archived: bool
    retention_expired: bool

    # Computed each request from the underlying governance artefacts.
    requirements: list[GateRequirementRead]
    can_advance: bool
    # At Retirement the requirements gate archiving rather than a next stage.
    can_archive: bool


class StageRevert(BaseModel):
    reason: str


class OwnerUpdate(BaseModel):
    owner_id: int | None = None


class DeploymentRecordUpdate(BaseModel):
    deployment_environment: str | None = None
    deployment_version: str | None = None
    deployed_at: date | None = None


class MonitoringUpdate(BaseModel):
    monitoring_owner_id: int | None = None
    incident_escalation_path: str | None = None


class RetirementUpdate(BaseModel):
    retirement_reason: str | None = None
    retention_until: date | None = None


class ArchivedAISystemRead(BaseModel):
    """One row of the archive listing."""

    ai_system_row_id: int
    name: str
    retirement_reason: str | None
    retired_at: date | None
    retention_until: date | None
    archived_at: datetime | None
    retention_expired: bool
