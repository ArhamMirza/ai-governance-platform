from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GovernanceRoleAssignment(Base):
    """One user holding one governance role. A user can hold several roles
    (e.g. Risk Owner and AI System Owner); most roles can have several
    holders too -- governance_role_service enforces each role's max_holders
    at assignment time, not here."""

    __tablename__ = "governance_role_assignments"
    __table_args__ = (
        UniqueConstraint("governance_role_id", "user_id", name="uq_governance_role_holder"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    governance_role_id: Mapped[int] = mapped_column(
        ForeignKey("governance_roles.id"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    assigned_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
