from datetime import date
from typing import Literal

from pydantic import BaseModel

ImportAction = Literal["create", "update", "unchanged", "skip"]


class UserImportRow(BaseModel):
    """What one line of the file would do."""

    line: int
    name: str
    email: str
    role: str | None
    action: ImportAction
    # Why a line is skipped, or what an update changes.
    note: str | None = None


class UserImportMissing(BaseModel):
    """An active account that is not in the file. Only ever a suggestion."""

    id: int
    name: str
    email: str
    role: str


class UserImportPreview(BaseModel):
    rows: list[UserImportRow]
    create: int
    update: int
    unchanged: int
    skip: int
    missing_from_file: list[UserImportMissing]


class UserImportCreated(BaseModel):
    name: str
    email: str
    role: str
    temporary_password: str


class UserImportResult(BaseModel):
    """What was done. The starting passwords are here and nowhere else."""

    created: list[UserImportCreated]
    updated: int
    unchanged: int
    skipped: list[UserImportRow]
    password_expires_on: date
    missing_from_file: list[UserImportMissing]
