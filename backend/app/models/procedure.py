from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProcedureStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    RETIRED = "retired"


class Procedure(Base):
    __tablename__ = "procedures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ProcedureStatus.DRAFT)
    version: Mapped[int] = mapped_column(Integer, default=1)
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_id: Mapped[int | None] = mapped_column(
        ForeignKey("policies.id"), nullable=True, index=True
    )
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
