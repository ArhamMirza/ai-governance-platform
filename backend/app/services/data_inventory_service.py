from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.sheet import Sheet, SheetRow
from app.repositories import sheet_repository
from app.schemas.sheet import ColumnDef
from app.services import audit_service, sheet_service

ENTITY_TYPE = "DataInventory"

DEFAULT_COLUMNS = [
    ColumnDef(key="dataset_name", label="Dataset Name"),
    ColumnDef(key="ai_system_row_id", label="AI System"),
    ColumnDef(key="data_type", label="Data Type"),
    ColumnDef(key="data_source", label="Data Source"),
    ColumnDef(key="personal_data_involved", label="Personal Data Involved"),
    ColumnDef(key="data_owner", label="Data Owner"),
    ColumnDef(key="classification", label="Classification"),
    ColumnDef(key="retention_period", label="Retention Period"),
    # ISO 42001 A.7 -- data for AI systems
    ColumnDef(key="data_acquisition", label="Data Acquisition (A.7.3)"),
    ColumnDef(key="data_quality_measures", label="Data Quality Measures (A.7.4)"),
    ColumnDef(key="data_provenance", label="Data Provenance (A.7.5)"),
    ColumnDef(key="data_preparation", label="Data Preparation (A.7.6)"),
]


def get_or_create_sheet(db: Session) -> Sheet:
    sheet = sheet_repository.get_by_entity_type(db, ENTITY_TYPE)
    if sheet is not None:
        return sheet
    return sheet_service.create_sheet(db, ENTITY_TYPE, "Data Inventory", DEFAULT_COLUMNS)


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
