from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FrameworkControlRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    framework: str
    code: str
    title: str
    description: str | None
    category: str


class FrameworkTagsUpdate(BaseModel):
    control_ids: list[int]


class TaggedItem(BaseModel):
    entity_type: str
    entity_id: int
    label: str


class FrameworkMappingEntry(BaseModel):
    id: int
    framework: str
    code: str
    title: str
    description: str | None
    category: str
    tagged_items: list[TaggedItem]


class FrameworkSoaEntryRead(BaseModel):
    id: int
    framework: str
    code: str
    title: str
    description: str | None
    applicability: str
    justification: str | None
    # None until a decision is actually recorded for this control.
    updated_at: datetime | None
    tagged_items: list[TaggedItem]


class FrameworkSoaEntryUpdate(BaseModel):
    applicability: str
    justification: str | None = None
