"""ISO/IEC 42001 Clause 4: context of the organization.

Unlike every other governance record, this one is organization-wide, not
scoped to an AI system -- there is exactly one of it for the whole
deployment, the same shape as the AI System Inventory sheet. It carries a
description of the organization and its overall use of AI, alongside two
sheets (see app.models.sheet) it owns: internal/external issues and
interested parties.

Approval is single-stage, gated by the CAIGO role -- the same shape
Policy uses -- but unlike a Policy, this record is continuously
maintained rather than superseded by a new version, so editing it after
approval withdraws the approval and returns it to draft (the same rule
risk_assessment_service.add_row/update_row applies to risk items) rather
than Policy's "only editable while draft".
"""

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OrganizationContextStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"


class OrganizationContext(Base):
    __tablename__ = "organization_context"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_usage_overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The ISO/IEC 22989 AI roles the organization holds (clause 4.1) -- codes
    # from app.core.ai_stakeholder_roles. Part of the approved context.
    ai_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default=OrganizationContextStatus.DRAFT)
    issues_sheet_id: Mapped[int] = mapped_column(ForeignKey("sheets.id"))
    interested_parties_sheet_id: Mapped[int] = mapped_column(ForeignKey("sheets.id"))
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Set on approval (see app.core.review_cadence), same as Policy.
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
