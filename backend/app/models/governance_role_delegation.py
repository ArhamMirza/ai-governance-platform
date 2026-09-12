from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_UNREVOKED = text("revoked_at IS NULL")


class GovernanceRoleDelegation(Base):
    """A time-boxed stand-in for a governance role -- lets is_caigo (and
    every approval gate that calls it) recognize a second person as the
    Chief AI Governance Officer for a bounded window, so one person's
    absence doesn't stall every approval that role gates. Revoked by
    setting revoked_at rather than deleting, so past coverage stays
    auditable."""

    __tablename__ = "governance_role_delegations"
    __table_args__ = (
        # A role has at most one standing delegation. Revoked rows are the
        # history, so they're excluded rather than counted -- which is also
        # why delegate_caigo revokes every unrevoked row and not just the
        # one that is active right now: an expired-but-unrevoked row would
        # otherwise block every delegation that came after it.
        Index(
            "uq_one_standing_delegation_per_role",
            "governance_role_id",
            unique=True,
            sqlite_where=_UNREVOKED,
            postgresql_where=_UNREVOKED,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    governance_role_id: Mapped[int] = mapped_column(
        ForeignKey("governance_roles.id"), index=True
    )
    delegate_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
