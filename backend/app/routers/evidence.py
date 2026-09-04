from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.schemas.evidence import EvidenceRead
from app.services import evidence_service

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("", response_model=list[EvidenceRead])
def list_evidence(
    entity_type: str,
    entity_id: int,
    folder_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[EvidenceRead]:
    return evidence_service.list_evidence(db, entity_type, entity_id, folder_id)


@router.post("", response_model=EvidenceRead, status_code=201)
def upload_evidence(
    entity_type: str = Form(...),
    entity_id: int = Form(...),
    folder_id: int | None = Form(default=None),
    description: str | None = Form(default=None),
    document_type: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> EvidenceRead:
    return evidence_service.upload_evidence(
        db, entity_type, entity_id, folder_id, file, description, actor_id, document_type
    )


@router.get("/{evidence_id}/download")
def download_evidence(evidence_id: int, db: Session = Depends(get_db)) -> FileResponse:
    evidence = evidence_service.get_evidence(db, evidence_id)
    return FileResponse(
        path=evidence.storage_path,
        filename=evidence.filename,
        media_type=evidence.content_type,
    )


@router.delete("/{evidence_id}", status_code=204)
def delete_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    evidence_service.delete_evidence(db, evidence_id, actor_id)
