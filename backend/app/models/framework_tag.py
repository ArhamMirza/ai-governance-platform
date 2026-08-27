from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FrameworkTag(Base):
    """Links one entity (Policy/Procedure/RiskAssessment, by entity_type +
    entity_id -- same polymorphic pattern as AuditLogEntry) to a control it is
    tagged against."""

    __tablename__ = "framework_tags"
    __table_args__ = (
        UniqueConstraint(
            "entity_type", "entity_id", "framework_control_id", name="uq_framework_tag_entity"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    framework_control_id: Mapped[int] = mapped_column(
        ForeignKey("framework_controls.id"), index=True
    )
