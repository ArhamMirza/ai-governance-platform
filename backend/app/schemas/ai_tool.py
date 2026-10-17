from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.ai_tool import AIToolRequestStatus, AIToolStatus, DataClassification
from app.schemas.framework_control import FrameworkControlRead


class AIToolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    vendor: str | None = None
    # Domains or URLs; stored as bare normalised domains.
    domains: list[str] = Field(min_length=1)
    description: str | None = None
    owner_id: int | None = None
    supplier_id: int | None = None


class AIToolUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    vendor: str | None = None
    domains: list[str] | None = Field(default=None, min_length=1)
    description: str | None = None
    owner_id: int | None = None
    supplier_id: int | None = None
    max_data_classification: DataClassification | None = None
    conditions_of_use: str | None = None
    review_due: date | None = None


class AIToolDecision(BaseModel):
    """The Chief AI Governance Officer's call on a tool. Approving or
    restricting says what data it may be given; revoking needs a reason."""

    action: Literal["approve", "restrict", "revoke"]
    max_data_classification: DataClassification | None = None
    conditions_of_use: str | None = None
    # Defaults to a year from the decision.
    review_due: date | None = None
    note: str | None = None


class AIToolStandingRead(BaseModel):
    """Computed, never stored: whether an approved tool is past its review."""

    review_overdue: bool


class AIToolRead(BaseModel):
    id: int
    name: str
    vendor: str | None
    domains: list[str]
    description: str | None
    status: AIToolStatus
    max_data_classification: DataClassification
    conditions_of_use: str | None
    owner_id: int | None
    supplier_id: int | None
    decided_by: int | None
    decided_on: date | None
    decision_note: str | None
    review_due: date | None
    standing: AIToolStandingRead
    framework_tags: list[FrameworkControlRead]
    created_at: datetime
    updated_at: datetime


class AIToolRequestCreate(BaseModel):
    """What an employee sends. Either a catalogued tool (`tool_id`) or a new
    one by name, with its address if they know it."""

    tool_id: int | None = None
    tool_name: str = Field(min_length=1, max_length=200)
    domain: str | None = None
    purpose: str = Field(min_length=10)
    data_involved: str | None = None


class AIToolRequestDecision(BaseModel):
    action: Literal["approve", "reject"]
    # The address to allow, when the request didn't carry one.
    domain: str | None = None
    max_data_classification: DataClassification | None = None
    conditions_of_use: str | None = None
    review_due: date | None = None
    note: str | None = None


class AIToolRequestRead(BaseModel):
    id: int
    requester_id: int
    tool_id: int | None
    tool_name: str
    domain: str | None
    purpose: str
    data_involved: str | None
    requested_on: date
    status: AIToolRequestStatus
    decided_by: int | None
    decided_on: date | None
    decision_note: str | None


class StaffAITool(BaseModel):
    """A tool an employee may use, and the rules that go with it -- only
    what they need to use it properly."""

    id: int
    name: str
    vendor: str | None
    domains: list[str]
    status: Literal["approved", "restricted"]
    max_data_classification: DataClassification
    conditions_of_use: str | None


class StaffAIToolRequestRead(BaseModel):
    """An employee's own request and how it was answered."""

    id: int
    tool_name: str
    domain: str | None
    purpose: str
    requested_on: date
    status: AIToolRequestStatus
    decided_on: date | None
    decision_note: str | None


class StaffRequestableTool(BaseModel):
    """A tool that is known but not allowed, for the request form's picker --
    its name only."""

    id: int
    name: str
    vendor: str | None
