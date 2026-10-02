from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SupplierRole(StrEnum):
    """What the supplier is, for one AI system, under the EU AI Act."""

    PROVIDER = "provider"  # They provide the AI system or its model.
    COMPONENT_SUPPLIER = "component_supplier"  # Tools, services, components, data (Art. 25(4)).
    IMPORTER = "importer"
    DISTRIBUTOR = "distributor"


class SupplierAISystem(Base):
    """A supplier contributing to one AI system. Removed (the supplier
    itself survives) when the AI system is deleted -- see
    supplier_service.unlink_ai_system.

    Also records what the organization has done with this supplier's
    system that would make the organization its provider under EU AI Act
    Art. 25(1) -- see art25_triggered."""

    __tablename__ = "supplier_ai_systems"
    __table_args__ = (
        UniqueConstraint("supplier_id", "ai_system_row_id", name="uq_supplier_ai_system"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    ai_system_row_id: Mapped[int] = mapped_column(ForeignKey("sheet_rows.id"), index=True)

    # None = not recorded yet.
    supplier_role: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Art. 25(1): the organization becomes the provider if it (a) puts its own
    # name or trademark on the system, (b) substantially modifies it, or (c)
    # changes its intended purpose so that it becomes high-risk.
    rebranded: Mapped[bool] = mapped_column(Boolean, default=False)
    substantially_modified: Mapped[bool] = mapped_column(Boolean, default=False)
    repurposed_to_high_risk: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def art25_triggered(self) -> bool:
        return bool(self.rebranded or self.substantially_modified or self.repurposed_to_high_risk)
