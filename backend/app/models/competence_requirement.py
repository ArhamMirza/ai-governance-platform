from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CompetenceRequirement(Base):
    """A competence or awareness the organization requires -- ISO/IEC 42001
    Clauses 7.2/7.3. E.g. "Bias testing" for AI System Owners, or "AI
    policy awareness" for everyone.

    Who it applies to is never stored as a list of people: it's the holders
    of governance_role_id (or every active user when that's None), worked
    out live, so assigning someone to a role puts them on the hook
    automatically. See competence_service.required_user_ids.
    """

    __tablename__ = "competence_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # None = everyone. A real FK: governance_role_service.delete_role
    # refuses to delete a role a requirement still targets.
    governance_role_id: Mapped[int | None] = mapped_column(
        ForeignKey("governance_roles.id"), nullable=True, index=True
    )
    # None = completing it once is enough; otherwise it must be refreshed.
    refresh_interval_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
