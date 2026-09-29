from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SupplierAISystem(Base):
    """A supplier contributing to one AI system. Removed (the supplier
    itself survives) when the AI system is deleted -- see
    supplier_service.unlink_ai_system."""

    __tablename__ = "supplier_ai_systems"
    __table_args__ = (
        UniqueConstraint("supplier_id", "ai_system_row_id", name="uq_supplier_ai_system"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    ai_system_row_id: Mapped[int] = mapped_column(ForeignKey("sheet_rows.id"), index=True)
