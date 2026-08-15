from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    action: str
    actor_id: int | None
    timestamp: datetime
    diff: dict | None
