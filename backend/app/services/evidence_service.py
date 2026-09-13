import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import Connection, Engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models.document_chunk import SourceType
from app.models.evidence import Evidence
from app.repositories import (
    document_index_repository,
    evidence_repository,
    folder_repository,
)
from app.services import audit_service, framework_service, policy_service, procedure_service

# Entity types whose "version" is a document-set change counter rather than a
# content diff (see DESIGN.md 4.2).
_DOCUMENT_VERSION_BUMP_HOOKS = {
    "Policy": policy_service.bump_version_if_draft,
    "Procedure": procedure_service.bump_version_if_draft,
}

# Risk items are the one entity whose evidence is load-bearing: a closed
# item is reopened if its last proof is deleted (see delete_evidence).
RISK_ITEM_ENTITY_TYPE = "RiskItem"

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
    document_type: str | None = None,
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
        document_type=document_type,
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


def index_in_background(bind: Engine | Connection, evidence_id: int) -> None:
    """Make one uploaded document searchable, after the upload has returned.

    Takes the bind the request was using rather than reaching for the global
    session factory. A background task needs its own session -- the request's
    is closed by the time this runs -- but it must be a session on the *same*
    database. Reaching for the global factory instead meant that anything
    which had swapped the database out from under the app, a test above all,
    got a background task quietly reading and writing somewhere else
    entirely.

    Never raises: the document is already stored and recorded, and a search
    gap belongs on the row, not thrown at a caller who has already left.
    """
    from app.services import document_index_service

    db = Session(bind=bind)
    try:
        document_index_service.index_quietly(db, evidence_id)
    finally:
        db.close()


def delete_all_for_entity(db: Session, entity_type: str, entity_id: int) -> None:
    """Cleans up every evidence file and folder for an entity that is itself
    being deleted (e.g. a risk item row, a draft policy). No per-file audit
    entry -- the parent entity's own "deleted" log entry already covers it,
    matching how framework tags are cleared on delete elsewhere.

    Looked up with list_for_entity, not list_at_level(..., folder_id=None):
    every entity type this is called for is reachable through the same
    folder-capable document browser in the UI, so evidence filed inside a
    subfolder is exactly as real as evidence filed flat, and was previously
    left behind by this function."""
    for evidence in evidence_repository.list_for_entity(db, entity_type, entity_id):
        Path(evidence.storage_path).unlink(missing_ok=True)
        # These documents can be tagged to framework controls too -- see
        # delete_evidence for why the tags can't outlive the file.
        framework_service.delete_tags(db, "Evidence", evidence.id)
        document_index_repository.clear_for_source(db, SourceType.EVIDENCE, evidence.id)
        evidence_repository.delete(db, evidence)
    folder_repository.delete_all_for_entity(db, entity_type, entity_id)


def delete_evidence(db: Session, evidence_id: int, actor_id: int | None) -> None:
    evidence = _get_or_raise(db, evidence_id)
    entity_type, entity_id, filename = evidence.entity_type, evidence.entity_id, evidence.filename
    Path(evidence.storage_path).unlink(missing_ok=True)
    # A document can be tagged to framework controls, and the Statement of
    # Applicability reads those tags as evidence that a control is covered.
    # Leaving them behind would keep a deleted document counting as coverage.
    framework_service.delete_tags(db, "Evidence", evidence_id)
    # The search index is three tables, only one of which has a foreign key
    # to this row -- and SQLite isn't running with foreign key enforcement
    # on anyway. Cleared explicitly, or a deleted document's text stays
    # retrievable and the assistant quotes a file that no longer exists.
    document_index_repository.clear_for_source(db, SourceType.EVIDENCE, evidence_id)
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
    if entity_type == RISK_ITEM_ENTITY_TYPE:
        # A risk item can't be closed without proof, so it mustn't stay closed
        # without one either. Imported here rather than at module scope:
        # risk_assessment_service imports this module.
        from app.services import risk_assessment_service

        risk_assessment_service.reopen_if_evidence_gone(db, entity_id, actor_id)
