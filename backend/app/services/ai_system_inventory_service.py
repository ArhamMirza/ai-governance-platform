from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.sheet import Sheet, SheetRow
from app.repositories import sheet_repository
from app.schemas.sheet import ColumnDef
from app.services import sheet_service

ENTITY_TYPE = "AISystemInventory"

DEFAULT_COLUMNS = [
    ColumnDef(key="name", label="Name"),
    ColumnDef(key="description", label="Description"),
    ColumnDef(key="purpose", label="Purpose"),
    ColumnDef(key="lifecycle_stage", label="Lifecycle Stage"),
    ColumnDef(key="risk_tier", label="Risk Tier"),
]


def get_or_create_sheet(db: Session) -> Sheet:
    sheet = sheet_repository.get_by_entity_type(db, ENTITY_TYPE)
    if sheet is not None:
        return sheet
    return sheet_service.create_sheet(db, ENTITY_TYPE, "AI System Inventory", DEFAULT_COLUMNS)


def list_rows(db: Session) -> list[SheetRow]:
    sheet = get_or_create_sheet(db)
    return sheet_service.list_rows(db, sheet.id)


def set_columns(db: Session, columns: list[ColumnDef]) -> Sheet:
    sheet = get_or_create_sheet(db)
    return sheet_service.set_columns(db, sheet.id, columns)


def add_row(db: Session, data: dict) -> SheetRow:
    sheet = get_or_create_sheet(db)
    return sheet_service.add_row(db, sheet.id, data)


def update_row(db: Session, row_id: int, data: dict) -> SheetRow:
    sheet = get_or_create_sheet(db)
    return sheet_service.update_row(db, sheet.id, row_id, data)


def delete_row(db: Session, row_id: int) -> None:
    sheet = get_or_create_sheet(db)
    sheet_service.delete_row(db, sheet.id, row_id)


def export_xlsx(db: Session) -> bytes:
    sheet = get_or_create_sheet(db)
    return sheet_service.export_xlsx(db, sheet.id)


def import_upload(db: Session, file: UploadFile) -> Sheet:
    sheet = get_or_create_sheet(db)
    return sheet_service.import_upload(db, sheet.id, file)
