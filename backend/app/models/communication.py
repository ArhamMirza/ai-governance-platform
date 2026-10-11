from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CommunicationDirection(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class CommunicationStatus(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"


class CommunicationPlanItem(Base):
    """One thing the organization has planned to communicate about the AI
    management system -- ISO/IEC 42001 7.4: on what, when, with whom, how,
    and who is responsible, internally and externally.

    A flat, fixed-schema record like Supplier. When it's next due is
    computed live from the records of it having been done
    (app.core.communication_schedule); an item with no interval is
    event-driven and never falls due."""

    __tablename__ = "communication_plan_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String(200))
    # Free text -- "all staff", "enterprise customers", "the regulator".
    audience: Mapped[str] = mapped_column(String(300))
    direction: Mapped[str] = mapped_column(String(10), default=CommunicationDirection.INTERNAL)
    method: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Bare nullable Integer, like Supplier.owner_id.
    responsible_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(10), default=CommunicationStatus.ACTIVE)

    # Both set, or both None -- see communication_service._validate. When
    # the first is due; after that, interval_months on from the latest.
    interval_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_due: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class CommunicationRecord(Base):
    """One time a planned communication was actually carried out. Supporting
    material (the notice sent, the slides, the minutes) attaches as evidence
    (entity_type="CommunicationRecord")."""

    __tablename__ = "communication_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    communication_id: Mapped[int] = mapped_column(
        ForeignKey("communication_plan_items.id"), index=True
    )
    communicated_on: Mapped[date] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
