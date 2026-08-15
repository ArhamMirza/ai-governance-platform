from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.sheet import Sheet, SheetRow
from app.repositories import sheet_repository
from app.schemas.sheet import ColumnDef
from app.services import audit_service, sheet_service

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


def set_columns(db: Session, columns: list[ColumnDef], actor_id: int | None) -> Sheet:
    sheet = get_or_create_sheet(db)
    result = sheet_service.set_columns(db, sheet.id, columns)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "columns_updated", actor_id)
    return result


def add_row(db: Session, data: dict, actor_id: int | None) -> SheetRow:
    sheet = get_or_create_sheet(db)
    row = sheet_service.add_row(db, sheet.id, data)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "row_added", actor_id, {"row_id": row.id})
    return row


def update_row(db: Session, row_id: int, data: dict, actor_id: int | None) -> SheetRow:
    sheet = get_or_create_sheet(db)
    row = sheet_service.update_row(db, sheet.id, row_id, data)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "row_updated", actor_id, {"row_id": row_id})
    return row


def delete_row(db: Session, row_id: int, actor_id: int | None) -> None:
    sheet = get_or_create_sheet(db)
    sheet_service.delete_row(db, sheet.id, row_id)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "row_deleted", actor_id, {"row_id": row_id})


def export_xlsx(db: Session) -> bytes:
    sheet = get_or_create_sheet(db)
    return sheet_service.export_xlsx(db, sheet.id)


def import_upload(db: Session, file: UploadFile, actor_id: int | None) -> Sheet:
    sheet = get_or_create_sheet(db)
    result = sheet_service.import_upload(db, sheet.id, file)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "sheet_uploaded", actor_id)
    return result
