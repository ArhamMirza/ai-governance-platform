from pydantic import BaseModel

from app.schemas.eu_ai_act import EuAiActScope
from app.schemas.framework_control import TaggedItem


class TaggedItemStatus(TaggedItem):
    """A tagged item, plus whether it currently counts toward the control
    being satisfied and why."""

    current: bool
    detail: str


class ControlComplianceStatus(BaseModel):
    id: int
    framework: str
    code: str
    title: str
    description: str | None
    category: str
    status: str
    reason: str
    tagged_items: list[TaggedItemStatus]


class ComplianceStatusCounts(BaseModel):
    satisfied: int
    partial: int
    no_coverage: int
    not_applicable: int


class ComplianceStatusSummary(BaseModel):
    iso_42001_clauses: ComplianceStatusCounts
    iso_42001_annex_a: ComplianceStatusCounts
    eu_ai_act: ComplianceStatusCounts
    # Whether the EU AI Act applies at all -- so an out-of-scope
    # organization's EU AI Act figures can be shown as such, not as zero.
    eu_ai_act_scope: EuAiActScope
