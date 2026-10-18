from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    # The rules (length and so on) are checked in the service, so the person
    # is told what is wrong in words rather than by a generic validation error.
    password: str = Field(min_length=1, max_length=200)
    # Only asked for on a real deployment (app.core.setup_code).
    setup_code: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    # True until the person chooses a password of their own; the app then
    # shows only the change-password screen.
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


class SessionsEnded(BaseModel):
    other_sessions_ended: int


class RegistrationStatus(BaseModel):
    registration_open: bool
    # True when the first account also needs the code from the server's log.
    setup_code_required: bool = False
