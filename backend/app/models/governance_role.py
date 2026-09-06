from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GovernanceRole(Base):
    """An organizational role describing who is responsible for what --
    independent of (but sometimes linked to, see governance_role_service's
    CAIGO rule) the technical admin/contributor/viewer permission a user
    holds. parent_role_id drives the org chart: each role reports to at
    most one other, laid out as a tree rather than freely positioned."""

    __tablename__ = "governance_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    responsibilities: Mapped[str] = mapped_column(Text)
    # None = unbounded holders. Only the seeded Chief AI Governance Officer
    # role is capped (at 1) today, but any admin-created role can be too.
    max_holders: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parent_role_id: Mapped[int | None] = mapped_column(
        ForeignKey("governance_roles.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
