from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SoaApplicability(StrEnum):
    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"


class FrameworkSoaEntry(Base):
    """Organization-wide Statement of Applicability decision for one Annex A
    control -- whether it applies, and why. One row per annex_a_control
    FrameworkControl, seeded by migration alongside the control itself."""

    __tablename__ = "framework_soa_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    framework_control_id: Mapped[int] = mapped_column(
        ForeignKey("framework_controls.id"), unique=True, index=True
    )
    applicability: Mapped[str] = mapped_column(
        String(20), default=SoaApplicability.APPLICABLE
    )
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
