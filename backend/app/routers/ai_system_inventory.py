from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.sheet import (
    ColumnsUpdate,
    RowCreate,
    RowUpdate,
    SheetRowRead,
    SheetWithRowsRead,
)
from app.services import ai_system_inventory_service

router = APIRouter(prefix="/ai-system-inventory", tags=["ai-system-inventory"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("", response_model=SheetWithRowsRead)
def get_inventory(db: Session = Depends(get_db)) -> SheetWithRowsRead:
    sheet = ai_system_inventory_service.get_or_create_sheet(db)
    rows = ai_system_inventory_service.list_rows(db)
    return SheetWithRowsRead(
        id=sheet.id,
        entity_type=sheet.entity_type,
        title=sheet.title,
        columns=sheet.columns,
        created_at=sheet.created_at,
        updated_at=sheet.updated_at,
        rows=rows,
    )


@router.put("/columns", response_model=SheetWithRowsRead)
def set_columns(data: ColumnsUpdate, db: Session = Depends(get_db)) -> SheetWithRowsRead:
    ai_system_inventory_service.set_columns(db, data.columns)
    return get_inventory(db)


@router.post("/rows", response_model=SheetRowRead, status_code=201)
def add_row(data: RowCreate, db: Session = Depends(get_db)) -> SheetRowRead:
    return ai_system_inventory_service.add_row(db, data.data)


@router.put("/rows/{row_id}", response_model=SheetRowRead)
def update_row(row_id: int, data: RowUpdate, db: Session = Depends(get_db)) -> SheetRowRead:
    return ai_system_inventory_service.update_row(db, row_id, data.data)


@router.delete("/rows/{row_id}", status_code=204)
def delete_row(row_id: int, db: Session = Depends(get_db)) -> None:
    ai_system_inventory_service.delete_row(db, row_id)


@router.post("/upload", response_model=SheetWithRowsRead)
def upload(file: UploadFile = File(...), db: Session = Depends(get_db)) -> SheetWithRowsRead:
    ai_system_inventory_service.import_upload(db, file)
    return get_inventory(db)


@router.get("/export")
def export(db: Session = Depends(get_db)) -> Response:
    content = ai_system_inventory_service.export_xlsx(db)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="ai_system_inventory.xlsx"'},
    )
