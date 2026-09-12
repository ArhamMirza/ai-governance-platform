from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DataInventoryStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"


class DataInventoryRecord(Base):
    """The review state of one Data Inventory row: the assigned Data Owner
    fills the dataset in and submits it, then the Chief AI Governance Officer
    approves it. One row per dataset (same sheet_rows FK AISystemLifecycle
    uses for the AI system inventory).

    Kept here rather than as sheet columns for the same reason the AI system's
    lifecycle stage is: these fields are typed, server-owned, and mustn't be
    editable -- or deletable -- from the grid."""

    __tablename__ = "data_inventory_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_inventory_row_id: Mapped[int] = mapped_column(
        ForeignKey("sheet_rows.id"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), default=DataInventoryStatus.DRAFT)

    # Who put it forward, and who signed it off. Plain Integer with no FK,
    # matching AISystemLifecycle.owner_id and the risk/impact approver columns.
    submitted_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
