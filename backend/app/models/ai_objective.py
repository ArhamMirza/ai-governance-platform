from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ObjectiveKind(StrEnum):
    # A metric with a target; on/off track is computed from recorded readings.
    MEASURED = "measured"
    # A qualitative goal ("publish a transparency notice"), tracked by its
    # target date -- 6.2 asks for measurable objectives only "if practicable".
    MILESTONE = "milestone"


class TargetDirection(StrEnum):
    AT_LEAST = "at_least"
    AT_MOST = "at_most"


class ObjectiveStatus(StrEnum):
    ACTIVE = "active"
    ACHIEVED = "achieved"
    NOT_ACHIEVED = "not_achieved"
    WITHDRAWN = "withdrawn"


class AIObjective(Base):
    """An AI objective and the plan to achieve it -- ISO/IEC 42001 6.2, with
    its readings (ObjectiveMeasurement) as the 9.1 monitoring evidence.

    A flat, fixed-schema record like Supplier. Where it stands is computed
    live (app.core.objective_tracking), never stored; only closing it --
    achieved, not achieved, withdrawn -- is a person's decision."""

    __tablename__ = "ai_objectives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(String(20), default=ObjectiveKind.MEASURED)
    # Bare nullable Integers, matching Supplier.owner_id: resolved at read
    # time; a deleted draft policy clears policy_id (objective_service.unlink_policy).
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # When the objective was set -- a management review dated before it
    # doesn't list it.
    established_on: Mapped[date] = mapped_column(Date)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # 6.2's plan: what will be done, with what resources, and how the
    # results will be evaluated.
    planned_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    resources: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_method: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Measured kind only -- see objective_service._validate.
    metric_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Both set, or both None, like Supplier's review schedule.
    measurement_interval_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_measurement_due: Mapped[date | None] = mapped_column(Date, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=ObjectiveStatus.ACTIVE)
    # Set when closed, so a standing as of an earlier date still sees it open.
    closed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    closure_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
