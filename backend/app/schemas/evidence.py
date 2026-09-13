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
    # Whether document search can see into this file, and why not when it
    # can't. On the read schema rather than kept internal, because a file
    # nobody can search is a gap the people responsible for the record
    # should be able to see.
    index_status: str
    index_detail: str | None
    # Text inside the document written to instruct a model. A finding about
    # the document, so it belongs on the document.
    injection_findings: list[str] | None
