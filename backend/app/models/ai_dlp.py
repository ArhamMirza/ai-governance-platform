from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import JSON, Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DLPRuleKind(StrEnum):
    BUILTIN = "builtin"
    KEYWORDS = "keywords"
    REGEX = "regex"


class DLPAction(StrEnum):
    """What the browser does when a rule matches (or an unapproved AI site is
    opened): note it, tell the person and let them go on, or stop it."""

    MONITOR = "monitor"
    WARN = "warn"
    BLOCK = "block"


class AIUsageEventType(StrEnum):
    UNAPPROVED_SITE = "unapproved_site"
    BLOCKED_SITE = "blocked_site"
    DLP_MATCH = "dlp_match"
    REQUEST_STARTED = "request_started"


class AIUsageAction(StrEnum):
    """What the extension actually did."""

    MONITORED = "monitored"
    WARNED = "warned"
    BLOCKED = "blocked"
    OVERRIDDEN = "overridden"


class DLPRule(Base):
    """One thing to stop being typed into an AI tool. Evaluated in the
    browser (app.core.dlp_rules) -- this row is only the definition."""

    __tablename__ = "dlp_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(String(20))
    # Which one of the three below is filled in depends on `kind`.
    builtin_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    # How sensitive the data it finds is. A tool approved for that class of
    # data (or a higher one) isn't held to the rule.
    classification: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(20), default=DLPAction.WARN)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AIUseSettings(Base):
    """How the organization's AI-use controls behave. One row, like
    ConcernSettings."""

    __tablename__ = "ai_use_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # What the browser does on a known AI site nobody has approved.
    unapproved_site_action: Mapped[str] = mapped_column(String(20), default=DLPAction.MONITOR)
    # How long usage counts are kept.
    retention_days: Mapped[int] = mapped_column(Integer, default=90)
    # Shown to staff: what is monitored and what is not. Transparency, and a
    # compliance requirement in many places.
    staff_notice: Mapped[str | None] = mapped_column(Text, nullable=True)
    # SHA-256 of the key the extension presents; the key itself is shown once.
    enrollment_key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enrollment_key_hint: Mapped[str | None] = mapped_column(String(8), nullable=True)
    enrollment_key_created_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class AIUsageEvent(Base):
    """A count, not a log: how many times, on one day, a person did one thing
    on one AI site. Never the page, the title, the text, or the time of day --
    just enough to see where the rules are biting."""

    __tablename__ = "ai_usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_ref: Mapped[str] = mapped_column(String(320), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    # A domain from the AI tool catalogue -- nothing else is ever recorded.
    domain: Mapped[str] = mapped_column(String(253))
    event_type: Mapped[str] = mapped_column(String(30))
    rule_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(20))
    count: Mapped[int] = mapped_column(Integer, default=1)


class AIAgentCheckin(Base):
    """That a person's browser has the extension and is reaching the platform:
    one row per person, holding the last day it reported in. A day and a
    version number, never a time of day, an address or a device -- enough to
    tell who is covered, not enough to follow anyone around."""

    __tablename__ = "ai_agent_checkins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_ref: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    first_seen: Mapped[date] = mapped_column(Date)
    last_seen: Mapped[date] = mapped_column(Date, index=True)
    extension_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
