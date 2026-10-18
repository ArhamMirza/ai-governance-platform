from pydantic import BaseModel, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)
    role: UserRole = UserRole.CONTRIBUTOR


class TemporaryPassword(BaseModel):
    """Shown once, to the administrator who asked for the reset."""

    temporary_password: str


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class UserAccountabilities(BaseModel):
    """What a user is on the hook for. Read before deactivating them: nobody
    can approve in their place, so anything they own is stuck until it is
    reassigned (see dashboard_service._invalid_owner_count)."""

    governance_roles: list[str] = []
    ai_systems_owned: list[str] = []
    datasets_owned: list[str] = []
    open_risk_items: int = 0
    pending_approvals: int = 0

    @property
    def is_empty(self) -> bool:
        return not (
            self.governance_roles
            or self.ai_systems_owned
            or self.datasets_owned
            or self.open_risk_items
            or self.pending_approvals
        )


class UserDirectoryEntry(BaseModel):
    """Minimal, non-admin-gated user info -- enough to populate an owner
    picker without exposing email/role/active-status to non-admins."""

    id: int
    name: str
    # Governance role names this user holds (Risk Owner, AI System Owner,
    # ...) -- every owner/assessor picker in the app badges its options with
    # this so the right person is obvious without hard-filtering the list.
    governance_roles: list[str] = []
