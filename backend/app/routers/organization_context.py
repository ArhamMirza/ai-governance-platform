from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id, get_current_approver_id
from app.schemas.organization_context import OrganizationContextRead, OrganizationContextUpdate
from app.schemas.sheet import ColumnsUpdate, RowCreate, RowUpdate, SheetRowRead, SheetWithRowsRead
from app.services import organization_context_service as service

router = APIRouter(prefix="/organization-context", tags=["organization-context"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("", response_model=OrganizationContextRead)
def get_organization_context(db: Session = Depends(get_db)) -> OrganizationContextRead:
    return service.get_or_create(db)


@router.put("", response_model=OrganizationContextRead)
def update_organization_context(
    data: OrganizationContextUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> OrganizationContextRead:
    return service.update(db, data.model_dump(exclude_unset=True), actor_id)


@router.post("/submit-for-review", response_model=OrganizationContextRead)
def submit_for_review(
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> OrganizationContextRead:
    return service.submit_for_review(db, actor_id)


@router.post("/approve", response_model=OrganizationContextRead)
def approve(
    db: Session = Depends(get_db),
    actor_id: int = Depends(get_current_approver_id),
) -> OrganizationContextRead:
    return service.approve(db, actor_id)


@router.get("/issues-sheet", response_model=SheetWithRowsRead)
def get_issues_sheet(db: Session = Depends(get_db)) -> SheetWithRowsRead:
    sheet = service.get_issues_sheet(db)
    return SheetWithRowsRead(
        id=sheet.id,
        entity_type=sheet.entity_type,
        title=sheet.title,
        columns=sheet.columns,
        created_at=sheet.created_at,
        updated_at=sheet.updated_at,
        rows=service.list_issues(db),
    )


@router.put("/issues-sheet/columns", response_model=SheetWithRowsRead)
def set_issues_columns(
    data: ColumnsUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> SheetWithRowsRead:
    service.set_issues_columns(db, data.columns, actor_id)
    return get_issues_sheet(db)


@router.post("/issues-sheet/upload", response_model=SheetWithRowsRead)
def upload_issues(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> SheetWithRowsRead:
    service.import_issues_upload(db, file, actor_id)
    return get_issues_sheet(db)


@router.get("/issues-sheet/export")
def export_issues(db: Session = Depends(get_db)) -> Response:
    content = service.export_issues_xlsx(db)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="organizational-issues.xlsx"'},
    )


@router.post("/issues", response_model=SheetRowRead, status_code=201)
def add_issue(
    data: RowCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> SheetRowRead:
    return service.add_issue(db, data.data, actor_id)


@router.put("/issues/{row_id}", response_model=SheetRowRead)
def update_issue(
    row_id: int,
    data: RowUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> SheetRowRead:
    return service.update_issue(db, row_id, data.data, actor_id)


@router.delete("/issues/{row_id}", status_code=204)
def delete_issue(
    row_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    service.delete_issue(db, row_id, actor_id)


@router.get("/interested-parties-sheet", response_model=SheetWithRowsRead)
def get_interested_parties_sheet(db: Session = Depends(get_db)) -> SheetWithRowsRead:
    sheet = service.get_interested_parties_sheet(db)
    return SheetWithRowsRead(
        id=sheet.id,
        entity_type=sheet.entity_type,
        title=sheet.title,
        columns=sheet.columns,
        created_at=sheet.created_at,
        updated_at=sheet.updated_at,
        rows=service.list_interested_parties(db),
    )


@router.put("/interested-parties-sheet/columns", response_model=SheetWithRowsRead)
def set_interested_parties_columns(
    data: ColumnsUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> SheetWithRowsRead:
    service.set_interested_parties_columns(db, data.columns, actor_id)
    return get_interested_parties_sheet(db)


@router.post("/interested-parties-sheet/upload", response_model=SheetWithRowsRead)
def upload_interested_parties(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> SheetWithRowsRead:
    service.import_interested_parties_upload(db, file, actor_id)
    return get_interested_parties_sheet(db)


@router.get("/interested-parties-sheet/export")
def export_interested_parties(db: Session = Depends(get_db)) -> Response:
    content = service.export_interested_parties_xlsx(db)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="interested-parties.xlsx"'},
    )


@router.post("/interested-parties", response_model=SheetRowRead, status_code=201)
def add_interested_party(
    data: RowCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> SheetRowRead:
    return service.add_interested_party(db, data.data, actor_id)


@router.put("/interested-parties/{row_id}", response_model=SheetRowRead)
def update_interested_party(
    row_id: int,
    data: RowUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> SheetRowRead:
    return service.update_interested_party(db, row_id, data.data, actor_id)


@router.delete("/interested-parties/{row_id}", status_code=204)
def delete_interested_party(
    row_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    service.delete_interested_party(db, row_id, actor_id)
