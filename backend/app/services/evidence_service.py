import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models.evidence import Evidence
from app.repositories import evidence_repository, folder_repository
from app.services import audit_service, policy_service, procedure_service

# Entity types whose "version" is a document-set change counter rather than a
# content diff (see DESIGN.md 4.2).
_DOCUMENT_VERSION_BUMP_HOOKS = {
    "Policy": policy_service.bump_version_if_draft,
    "Procedure": procedure_service.bump_version_if_draft,
}

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".csv",
    ".png",
    ".jpg",
    ".jpeg",
    ".txt",
    ".md",
}
MAX_SIZE_BYTES = 25 * 1024 * 1024


def _storage_dir() -> Path:
    path = Path(get_settings().evidence_storage_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_or_raise(db: Session, evidence_id: int) -> Evidence:
    evidence = evidence_repository.get(db, evidence_id)
    if evidence is None:
        raise NotFoundError("Evidence", evidence_id)
    return evidence


def list_evidence(
    db: Session, entity_type: str, entity_id: int, folder_id: int | None
) -> list[Evidence]:
    return evidence_repository.list_at_level(db, entity_type, entity_id, folder_id)


def get_evidence(db: Session, evidence_id: int) -> Evidence:
    return _get_or_raise(db, evidence_id)


def upload_evidence(
    db: Session,
    entity_type: str,
    entity_id: int,
    folder_id: int | None,
    file: UploadFile,
    description: str | None,
    actor_id: int | None,
) -> Evidence:
    if folder_id is not None:
        folder = folder_repository.get(db, folder_id)
        if folder is None:
            raise NotFoundError("Folder", folder_id)
        if folder.entity_type != entity_type or folder.entity_id != entity_id:
            raise ValidationError("folder_id does not belong to the given entity_type/entity_id")

    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"File type '{extension}' is not allowed. Allowed types: "
            f"{', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    contents = file.file.read()
    if len(contents) > MAX_SIZE_BYTES:
        raise ValidationError(f"File exceeds the {MAX_SIZE_BYTES // (1024 * 1024)}MB limit")

    stored_name = f"{uuid.uuid4().hex}{extension}"
    storage_path = _storage_dir() / stored_name
    storage_path.write_bytes(contents)

    evidence = Evidence(
        entity_type=entity_type,
        entity_id=entity_id,
        folder_id=folder_id,
        filename=file.filename or stored_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(contents),
        storage_path=str(storage_path),
        description=description,
        uploaded_by=actor_id,
    )
    evidence = evidence_repository.create(db, evidence)
    audit_service.log(
        db,
        entity_type,
        entity_id,
        "document_added",
        actor_id,
        {"evidence_id": evidence.id, "filename": evidence.filename},
    )
    if bump_hook := _DOCUMENT_VERSION_BUMP_HOOKS.get(entity_type):
        bump_hook(db, entity_id)
    return evidence


def delete_evidence(db: Session, evidence_id: int, actor_id: int | None) -> None:
    evidence = _get_or_raise(db, evidence_id)
    entity_type, entity_id, filename = evidence.entity_type, evidence.entity_id, evidence.filename
    Path(evidence.storage_path).unlink(missing_ok=True)
    evidence_repository.delete(db, evidence)
    audit_service.log(
        db,
        entity_type,
        entity_id,
        "document_removed",
        actor_id,
        {"evidence_id": evidence_id, "filename": filename},
    )
    if bump_hook := _DOCUMENT_VERSION_BUMP_HOOKS.get(entity_type):
        bump_hook(db, entity_id)
