from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AIObjectiveAISystem(Base):
    """An objective measuring or concerning one AI system. Removed (the
    objective itself survives) when the AI system is deleted -- see
    objective_service.unlink_ai_system."""

    __tablename__ = "ai_objective_ai_systems"
    __table_args__ = (
        UniqueConstraint("objective_id", "ai_system_row_id", name="uq_ai_objective_ai_system"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    objective_id: Mapped[int] = mapped_column(ForeignKey("ai_objectives.id"), index=True)
    ai_system_row_id: Mapped[int] = mapped_column(ForeignKey("sheet_rows.id"), index=True)
