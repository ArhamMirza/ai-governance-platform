from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SupplierType(StrEnum):
    MODEL_PROVIDER = "model_provider"
    DATA_PROVIDER = "data_provider"
    INFRASTRUCTURE = "infrastructure"
    SOFTWARE = "software"
    SERVICES = "services"
    OTHER = "other"


class SupplierStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Supplier(Base):
    """A third party behind the organization's AI systems -- a model
    provider, a data vendor, hosting, a consultancy. ISO/IEC 42001 A.10.2
    (allocating responsibilities) and A.10.3 (supplier requirements).

    A flat, fixed-schema record like CorrectiveAction. Contracts and DPAs
    attach as evidence (entity_type="Supplier"); periodic reviews live in
    SupplierReview; which AI systems it contributes to lives in
    SupplierAISystem.
    """

    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    supplier_type: Mapped[str] = mapped_column(String(30), default=SupplierType.OTHER)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=SupplierStatus.ACTIVE)
    # Bare nullable Integer, matching CorrectiveAction.assignee_id -- who owns
    # the relationship; resolved against users at read time.
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    contract_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contract_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    # A.10.2 -- who does what between the organization and this supplier.
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A.10.3 -- what the organization requires of them.
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Both set, or both None -- see supplier_service._validate. When the
    # first review is due; after that, interval_months on from the latest.
    review_interval_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_review_due: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
