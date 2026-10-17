from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import JSON, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AIToolStatus(StrEnum):
    """Where a tool stands with the organization. `catalogued` is a known AI
    site nobody has approved -- the state every tool starts in."""

    CATALOGUED = "catalogued"
    APPROVED = "approved"
    RESTRICTED = "restricted"
    REVOKED = "revoked"


class DataClassification(StrEnum):
    """The most sensitive data a tool may be given."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


class AIToolRequestStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"


class AITool(Base):
    """A third-party AI tool employees might use, and whether they may.

    Every tool the organization knows of is here, approved or not: the
    browser extension watches the catalogued sites and lets through the
    approved ones. Approval is the Chief AI Governance Officer's decision
    (ai_tool_service). Whether its review is overdue is computed from
    `review_due`, never stored."""

    __tablename__ = "ai_tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    vendor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Normalised domains the tool is reached at -- see app.core.ai_tool_domains.
    domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=AIToolStatus.CATALOGUED)
    max_data_classification: Mapped[str] = mapped_column(
        String(20), default=DataClassification.PUBLIC
    )
    conditions_of_use: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Bare nullable Integers, like Supplier.owner_id -- resolved at read time.
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    decided_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decided_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_due: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AIToolRequest(Base):
    """An employee asking for a tool to be allowed. Decided by the Chief AI
    Governance Officer; approving it approves the tool."""

    __tablename__ = "ai_tool_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requester_id: Mapped[int] = mapped_column(Integer, index=True)
    # The tool asked for, when it is already in the catalogue.
    tool_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(200))
    domain: Mapped[str | None] = mapped_column(String(253), nullable=True)
    purpose: Mapped[str] = mapped_column(Text)
    data_involved: Mapped[str | None] = mapped_column(Text, nullable=True)

    requested_on: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default=AIToolRequestStatus.REQUESTED)
    decided_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decided_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
