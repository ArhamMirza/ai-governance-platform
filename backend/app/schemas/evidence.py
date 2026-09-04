from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    folder_id: int | None
    filename: str
    content_type: str
    size_bytes: int
    description: str | None
    document_type: str | None
    uploaded_by: int | None
    uploaded_at: datetime
