from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.ai_draft import DraftCoverageGapRead, DraftSourceRead


class SuggestionRead(BaseModel):
    """One candidate risk item the model proposed, and how well supported it is."""

    key: str
    category: str | None = None
    description: str | None = None
    mitigation: str | None = None
    likelihood: int | None = None
    impact: int | None = None
    citations: list[int] = []
    # What the records were missing, where they didn't support proposing it.
    gap: str | None = None
    # Has content but no source behind it -- shown, flagged for extra scrutiny.
    uncited: bool = False
    # Every source it cited was invented, or it had no content at all.
    withheld: bool = False


class RiskSuggestionsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    provider: str
    model: str
    requested_by: int | None
    created_at: datetime
    proposals: list[SuggestionRead]
    sources: list[DraftSourceRead]
    injection_findings: list[str] | None = None
    coverage_gaps: list[DraftCoverageGapRead] | None = None


class AcceptedRiskItem(BaseModel):
    key: str
    category: str
    description: str
    mitigation: str | None = None
    likelihood: int | None = None
    impact: int | None = None
    risk_owner: str | None = None


class ApplySuggestionsRequest(BaseModel):
    # Only the items being added. Anything left out is not created.
    accepted: list[AcceptedRiskItem]
