"""The employee home -- the only routes an employee login can reach, beyond
signing in and out. Mounted with plain get_current_user in app.main, unlike
every other router (which refuses employees)."""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.staff import StaffLibraryItem
from app.services import staff_service

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/library", response_model=list[StaffLibraryItem])
def library(db: Session = Depends(get_db)) -> list[StaffLibraryItem]:
    return staff_service.library(db)


@router.get("/library/documents/{evidence_id}")
def download_document(evidence_id: int, db: Session = Depends(get_db)) -> FileResponse:
    evidence = staff_service.shared_document(db, evidence_id)
    return FileResponse(
        path=evidence.storage_path,
        filename=evidence.filename,
        media_type=evidence.content_type,
    )
