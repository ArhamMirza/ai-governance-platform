from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FolderCreate(BaseModel):
    entity_type: str
    entity_id: int
    name: str
    parent_folder_id: int | None = None


class FolderUpdate(BaseModel):
    name: str


class FolderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    parent_folder_id: int | None
    name: str
    created_at: datetime
