from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.organization_context import OrganizationContextStatus


class OrganizationContextUpdate(BaseModel):
    organization_description: str | None = None
    ai_usage_overview: str | None = None
    ai_roles: list[str] | None = None


class OrganizationContextRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_description: str | None
    ai_usage_overview: str | None
    ai_roles: list[str]
    status: OrganizationContextStatus
    approved_by: int | None
    approved_at: datetime | None
    next_review_date: date | None
    created_at: datetime
    updated_at: datetime
