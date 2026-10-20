from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.ai_draft import DraftCoverageGapRead, DraftSourceRead


class ContextProposalRead(BaseModel):
    """One thing the model proposed -- a narrative field, an issue, or an
    interested party -- and how well supported it is."""

    key: str
    kind: str  # "narrative" | "issue" | "party"
    field: str | None = None
    label: str | None = None
    value: str | None = None
    category: str | None = None
    issue: str | None = None
    planned_response: str | None = None
    party: str | None = None
    needs: str | None = None
    expectations: str | None = None
    requirements: str | None = None
    citations: list[int] = []
    gap: str | None = None
    uncited: bool = False
    withheld: bool = False


class OrganizationContextDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    provider: str
    model: str
    requested_by: int | None
    created_at: datetime
    proposals: list[ContextProposalRead]
    sources: list[DraftSourceRead]
    injection_findings: list[str] | None = None
    coverage_gaps: list[DraftCoverageGapRead] | None = None


class AcceptedNarrativeField(BaseModel):
    key: str
    value: str


class AcceptedIssueRow(BaseModel):
    key: str
    category: str
    issue: str
    planned_response: str | None = None


class AcceptedInterestedParty(BaseModel):
    key: str
    party: str
    needs: str | None = None
    expectations: str | None = None
    requirements: str | None = None


class ApplyOrganizationContextDraftRequest(BaseModel):
    narrative: list[AcceptedNarrativeField] = []
    issues: list[AcceptedIssueRow] = []
    interested_parties: list[AcceptedInterestedParty] = []


class DraftSourceReadiness(BaseModel):
    """One kind of record the draft reads, and how much of it there is."""

    key: str
    label: str
    count: int
    href: str
    # What the draft cannot say while this is empty.
    empty_note: str
