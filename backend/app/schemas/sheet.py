from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ColumnDef(BaseModel):
    key: str
    label: str
    data_type: str = "text"


class SheetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    title: str
    columns: list[ColumnDef]
    created_at: datetime
    updated_at: datetime


class SheetRowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sheet_id: int
    row_index: int
    data: dict
    created_at: datetime
    updated_at: datetime


class SheetWithRowsRead(SheetRead):
    rows: list[SheetRowRead]


class ColumnsUpdate(BaseModel):
    columns: list[ColumnDef]


class RowCreate(BaseModel):
    data: dict


class RowUpdate(BaseModel):
    data: dict
