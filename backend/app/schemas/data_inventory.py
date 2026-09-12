from datetime import datetime

from pydantic import BaseModel


class DataInventoryRecordRead(BaseModel):
    """The review state of one dataset entry. Approver/submitter names are
    resolved server-side so the grid doesn't need a second lookup."""

    data_inventory_row_id: int
    status: str
    submitted_by: int | None
    submitted_by_name: str | None
    submitted_at: datetime | None
    approved_by: int | None
    approved_by_name: str | None
    approved_at: datetime | None
