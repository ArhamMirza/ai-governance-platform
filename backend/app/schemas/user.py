from pydantic import BaseModel, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)
    role: UserRole = UserRole.CONTRIBUTOR


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
