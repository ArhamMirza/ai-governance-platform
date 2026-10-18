from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserMFA(Base):
    """A person's authenticator app. The secret is stored encrypted (the key is
    derived from the deployment secret), so a copy of the database alone does
    not hand over working codes. Until `confirmed`, it is a set-up in progress
    and does not affect sign-in."""

    __tablename__ = "user_mfa"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    secret_encrypted: Mapped[str] = mapped_column(String(400))
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # The 30-second step of the last code accepted, so the same code can't be
    # used twice.
    last_used_step: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MFARecoveryCode(Base):
    """One single-use code. Only its hash is kept."""

    __tablename__ = "mfa_recovery_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SecuritySettings(Base):
    """Organization-wide sign-in rules. One row, provisioned on first use."""

    __tablename__ = "security_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Off until an administrator switches it on, so enabling it can't lock out
    # accounts that haven't had the chance to set up an authenticator.
    require_mfa_for_admins: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
