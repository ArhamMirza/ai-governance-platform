from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AiAssistSettingsUpdate(BaseModel):
    provider: str
    model: str
    fast_model: str | None = None
    # Write-only. Omitted entirely = leave the stored key alone; "" = clear
    # it. That distinction matters, or re-saving the form with the key field
    # blank (which is all anyone ever sees) would wipe the credential.
    api_key: str | None = None
    base_url: str | None = None
    daily_token_budget: int = Field(default=200_000, ge=0)


class AiAssistSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    model: str
    fast_model: str | None
    base_url: str | None
    daily_token_budget: int
    # The key itself never leaves the server -- only whether one is set,
    # the way a password field never round-trips.
    has_api_key: bool
    updated_at: datetime | None


class AiAssistStatus(BaseModel):
    """What the frontend needs to decide whether to offer AI at all."""

    available: bool
    provider: str | None
    model: str | None
    # True when the configured provider runs inside the deployment, so the
    # UI can say plainly whether record content leaves the building.
    is_local: bool
    reason: str | None


class DraftRequest(BaseModel):
    kind: str
    impact_assessment_id: int
    factor: str | None = None


class DraftResponse(BaseModel):
    draft: str
    # Surfaced to the user when record content contained text that reads as
    # an instruction to a model -- a finding, not a silent event.
    injection_findings: list[str] = []
