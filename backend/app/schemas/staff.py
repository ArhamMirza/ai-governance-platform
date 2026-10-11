from datetime import date
from typing import Literal

from pydantic import BaseModel


class SharingUpdate(BaseModel):
    """Whether a policy or procedure is shared with employees."""

    shared_with_employees: bool


class StaffDocument(BaseModel):
    id: int
    filename: str
    content_type: str
    size_bytes: int


class StaffLibraryItem(BaseModel):
    """An approved policy or procedure an employee can read -- and nothing
    more of it than this: no owner, no review history, no tags."""

    kind: Literal["policy", "procedure"]
    id: int
    title: str
    description: str | None
    version: int
    effective_date: date | None
    documents: list[StaffDocument]
