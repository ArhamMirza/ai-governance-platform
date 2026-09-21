from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProposalRead(BaseModel):
    """One field the model proposed, and how well supported it is."""

    key: str
    section: str
    field: str
    factor: str | None = None
    label: str
    value: str | int | None = None
    # For a proposed score, the one-sentence reason for it.
    rationale: str | None = None
    citations: list[int] = []
    # What the records were missing, where they didn't support drafting it.
    gap: str | None = None
    # Text with no source behind it -- shown, but flagged for extra scrutiny.
    uncited: bool = False
    # Every source it cited was invented, so its text is not shown at all.
    withheld: bool = False


class DraftSourceRead(BaseModel):
    n: int
    title: str
    section: str | None = None
    kind: str
    href: str | None = None
    download_evidence_id: int | None = None
    read_by_ocr: bool = False
    excerpt: str
    injection_findings: list[str] = []


class DraftCoverageGapRead(BaseModel):
    evidence_id: int
    filename: str
    detail: str | None = None


class AiDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    provider: str
    model: str
    requested_by: int | None
    created_at: datetime
    proposals: list[ProposalRead]
    sources: list[DraftSourceRead]
    injection_findings: list[str] | None = None
    coverage_gaps: list[DraftCoverageGapRead] | None = None


class AcceptedField(BaseModel):
    key: str
    # What to save: the drafted value, or the reviewer's edit of it.
    value: str | int | None = None


class ApplyDraftRequest(BaseModel):
    # Only the fields being applied. Anything left out keeps its current value.
    accepted: list[AcceptedField]


class GenerateDraftRequest(BaseModel):
    """Optional guidance layered on top of what the draft would otherwise
    gather on its own -- scope, emphasis or tone, not another source.
    Shared by every drafting feature's generate endpoint."""

    instructions: str | None = None
