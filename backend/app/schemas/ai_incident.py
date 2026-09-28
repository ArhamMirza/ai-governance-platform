from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.core.incident_reporting import SeriousIncidentCategory
from app.models.ai_incident import AIIncidentSeverity, AIIncidentStatus
from app.schemas.framework_control import FrameworkControlRead


class AIIncidentCreate(BaseModel):
    title: str
    description: str
    ai_system_row_id: int | None = None
    detected_on: date
    occurred_on: date | None = None
    severity: AIIncidentSeverity = AIIncidentSeverity.MEDIUM
    owner_id: int | None = None
    is_serious: bool = False
    serious_category: SeriousIncidentCategory | None = None


class AIIncidentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    ai_system_row_id: int | None = None
    detected_on: date | None = None
    occurred_on: date | None = None
    severity: AIIncidentSeverity | None = None
    status: AIIncidentStatus | None = None
    owner_id: int | None = None
    impact_description: str | None = None
    immediate_actions: str | None = None
    root_cause: str | None = None
    is_serious: bool | None = None
    serious_category: SeriousIncidentCategory | None = None
    authority_notified_on: date | None = None
    authority_reference: str | None = None


class AIIncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    ai_system_row_id: int | None
    detected_on: date
    occurred_on: date | None
    severity: AIIncidentSeverity
    status: AIIncidentStatus
    owner_id: int | None
    impact_description: str | None
    immediate_actions: str | None
    root_cause: str | None
    is_serious: bool
    serious_category: SeriousIncidentCategory | None
    authority_notified_on: date | None
    authority_reference: str | None
    reporting_deadline: date | None
    reporting_overdue: bool
    corrective_action_ids: list[int]
    framework_tags: list[FrameworkControlRead]
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime
