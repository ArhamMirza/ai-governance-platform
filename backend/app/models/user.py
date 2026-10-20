from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy import false as sa_false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(StrEnum):
    ADMIN = "admin"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"
    # Staff who use AI systems but not this platform: a login that reaches
    # only the employee home (app.routers.staff_portal). It holds no Action
    # in app.core.permissions, and every other router refuses it -- see
    # app.dependencies.get_internal_user.
    EMPLOYEE = "employee"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default=UserRole.ADMIN)
    # A deactivated user can't log in or use an existing session (see
    # dependencies.get_current_user), but keeps their audit history intact --
    # deactivation, not deletion.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Set when an admin created the account or reset its password (the person
    # is using a password someone else knows), or when sign-in shows the
    # password falls short of the current rules. Until it is changed, the
    # login reaches only the change-password screen.
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=sa_false()
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # When a password an administrator issued stops working if it has not been
    # used to sign in and replaced. Empty for a password the person chose.
    temporary_password_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Their authenticator app, if they have started setting one up (app.models.mfa).
    mfa = relationship("UserMFA", uselist=False, lazy="joined", cascade="all, delete-orphan")

    @property
    def mfa_enabled(self) -> bool:
        return self.mfa is not None and self.mfa.confirmed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
