from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.ai_dlp import (
    AIUsageAction,
    AIUsageEventType,
    DLPAction,
    DLPRuleKind,
)
from app.models.ai_tool import AIToolStatus, DataClassification
from app.schemas.framework_control import FrameworkControlRead

# ---------- DLP rules ----------


class DLPRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    kind: DLPRuleKind
    # Whichever of these the kind needs; the others are ignored.
    builtin_key: str | None = None
    keywords: list[str] | None = None
    pattern: str | None = None
    classification: DataClassification
    action: DLPAction = DLPAction.WARN
    enabled: bool = True


class DLPRuleUpdate(BaseModel):
    """The kind of rule can't change: make a new one instead."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    builtin_key: str | None = None
    keywords: list[str] | None = None
    pattern: str | None = None
    classification: DataClassification | None = None
    action: DLPAction | None = None
    enabled: bool | None = None


class DLPRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    kind: DLPRuleKind
    builtin_key: str | None
    keywords: list[str] | None
    pattern: str | None
    classification: DataClassification
    action: DLPAction
    enabled: bool
    created_at: datetime
    updated_at: datetime


class BuiltinDetectorRead(BaseModel):
    key: str
    label: str
    description: str


# ---------- settings ----------


class AIUseSettingsRead(BaseModel):
    id: int
    unapproved_site_action: DLPAction
    retention_days: int
    staff_notice: str | None
    # Whether a key has been issued, never the key.
    enrollment_key_issued: bool
    enrollment_key_hint: str | None
    enrollment_key_created_on: date | None
    framework_tags: list[FrameworkControlRead]


class AIUseSettingsUpdate(BaseModel):
    unapproved_site_action: DLPAction | None = None
    retention_days: int | None = Field(default=None, ge=7, le=730)
    staff_notice: str | None = None


class EnrollmentKeyIssued(BaseModel):
    """The only time the key is ever shown."""

    key: str
    hint: str


# ---------- what the extension reads and sends ----------


class AgentTool(BaseModel):
    name: str
    domains: list[str]
    status: AIToolStatus
    max_data_classification: DataClassification


class AgentRule(BaseModel):
    id: int
    name: str
    kind: DLPRuleKind
    builtin_key: str | None
    keywords: list[str] | None
    pattern: str | None
    classification: DataClassification
    action: DLPAction


class AgentPolicy(BaseModel):
    """Everything the extension needs, and nothing it doesn't. Its ETag is a
    hash of this, so an unchanged policy costs a 304."""

    unapproved_site_action: DLPAction
    staff_notice: str | None
    tools: list[AgentTool]
    rules: list[AgentRule]


class AgentEvent(BaseModel):
    """One day's count of one thing. Unknown fields are refused outright, so
    nothing but these can be sent -- not a URL, not a page title, not text."""

    model_config = ConfigDict(extra="forbid")

    day: date
    domain: str = Field(min_length=3, max_length=253)
    event_type: AIUsageEventType
    rule_id: int | None = None
    action: AIUsageAction
    count: int = Field(ge=1, le=10_000)


class AgentEvents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_email: str = Field(min_length=3, max_length=320)
    events: list[AgentEvent] = Field(min_length=1, max_length=500)


class AgentEventsAccepted(BaseModel):
    accepted: int


# ---------- the usage dashboard ----------


class UsageByType(BaseModel):
    event_type: AIUsageEventType
    count: int


class UsageByDomain(BaseModel):
    domain: str
    tool_name: str | None
    status: AIToolStatus | None
    unapproved: int
    blocked: int
    dlp_matches: int


class UsageByRule(BaseModel):
    rule_id: int
    rule_name: str | None
    matches: int
    blocked: int


class UsageByUser(BaseModel):
    user_ref: str
    user_name: str | None
    unapproved: int
    dlp_matches: int


class UsageByDay(BaseModel):
    day: date
    unapproved: int
    dlp_matches: int


class UsageSummary(BaseModel):
    days: int
    by_type: list[UsageByType]
    by_domain: list[UsageByDomain]
    by_rule: list[UsageByRule]
    by_user: list[UsageByUser]
    by_day: list[UsageByDay]


class StaffAIUseNotice(BaseModel):
    """What staff are told about how AI use is monitored."""

    staff_notice: str | None
    unapproved_site_action: Literal["monitor", "warn", "block"]
