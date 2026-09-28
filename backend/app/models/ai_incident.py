from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AIIncidentSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AIIncidentStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"


class AIIncident(Base):
    """Something that went wrong with an AI system in operation -- a harmful
    output, a misclassification, a complaint, a near-miss. ISO/IEC 42001
    A.8.4 and EU AI Act Art. 73.

    A flat, independent record like CorrectiveAction. Remediation isn't
    tracked here: a CorrectiveAction raised from an incident points back at
    it through its own (source_type="AIIncident", source_id) pair, the same
    way one raised from an audit finding does.
    """

    __tablename__ = "ai_incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)

    # Optional -- not every incident is about one system. Unlinked (not
    # deleted) when its system is deleted: an incident is history, and
    # outlives the system the way a dataset does.
    ai_system_row_id: Mapped[int | None] = mapped_column(
        ForeignKey("sheet_rows.id"), nullable=True, index=True
    )

    # When the organization became aware of it -- Art. 73's reporting
    # deadline counts from here, not from when it happened.
    detected_on: Mapped[date] = mapped_column(Date)
    occurred_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    severity: Mapped[str] = mapped_column(String(20), default=AIIncidentSeverity.MEDIUM)
    status: Mapped[str] = mapped_column(String(20), default=AIIncidentStatus.OPEN)
    # Bare nullable Integer, matching CorrectiveAction.assignee_id -- no
    # DB-level FK; resolved against users at read time.
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    impact_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    immediate_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)

    # EU AI Act Art. 73 -- see app.core.incident_reporting for the deadline.
    is_serious: Mapped[bool] = mapped_column(Boolean, default=False)
    serious_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    authority_notified_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    authority_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
