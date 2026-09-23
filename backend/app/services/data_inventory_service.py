"""The Data Inventory sheet, and the review each dataset entry goes through.

Datasets are recorded as sheet rows (like the AI system inventory), but their
review state lives in a typed DataInventoryRecord sidecar table so it is
server-owned and can't be edited away in the grid -- the same split
AISystemLifecycle uses for an AI system's stage.

The workflow is two-stage: the Data Owner named on the row fills it in and
submits it, then the Chief AI Governance Officer approves it. Only that
assigned owner (or an admin) may edit the row, and any edit sends an
already-reviewed entry back to draft so an approval always describes the data
as it currently stands.
"""

from datetime import UTC, datetime

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.concurrency import claim_transition, create_or_get, withdraw_transition
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.models.data_inventory_record import DataInventoryRecord, DataInventoryStatus
from app.models.sheet import Sheet, SheetRow
from app.models.user import User, UserRole
from app.repositories import data_inventory_record_repository, sheet_repository
from app.schemas.sheet import ColumnDef
from app.services import audit_service, governance_role_service, sheet_service

ENTITY_TYPE = "DataInventory"
# A distinct entity type for the sign-off, so the segregation-of-duties lookup
# never sees an ordinary row edit -- same split as AISystemDeploymentApproval.
APPROVAL_ENTITY_TYPE = "DataInventoryApproval"

STATUS_COLUMN_KEY = "approval_status"
OWNER_COLUMN_KEY = "data_owner"
NAME_COLUMN_KEY = "dataset_name"
AI_SYSTEM_COLUMN_KEY = "ai_system_row_id"

DEFAULT_COLUMNS = [
    ColumnDef(key="dataset_name", label="Dataset Name"),
    ColumnDef(key=AI_SYSTEM_COLUMN_KEY, label="AI System"),
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
    ColumnDef(key=STATUS_COLUMN_KEY, label="Approval Status"),
]


def get_or_create_sheet(db: Session) -> Sheet:
    return sheet_service.get_or_create_singleton_sheet(
        db, ENTITY_TYPE, "Data Inventory", DEFAULT_COLUMNS
    )


def list_rows(db: Session) -> list[SheetRow]:
    sheet = get_or_create_sheet(db)
    return sheet_service.list_rows(db, sheet.id)


def _get_row_or_raise(db: Session, row_id: int) -> SheetRow:
    sheet = get_or_create_sheet(db)
    row = sheet_repository.get_row(db, row_id)
    if row is None or row.sheet_id != sheet.id:
        raise NotFoundError("SheetRow", row_id)
    return row


# ---------- review state ----------


def get_or_create_record(db: Session, row_id: int) -> DataInventoryRecord:
    """Every dataset entry has a review record; one is created at draft on
    first request. Lazy rather than eager so rows that predate this feature --
    and rows recreated by an xlsx import -- are covered too."""
    _get_row_or_raise(db, row_id)
    existing = data_inventory_record_repository.get_for_row(db, row_id)
    if existing is not None:
        return existing
    # Two simultaneous first requests both get here; the unique constraint on
    # data_inventory_row_id lets one through and hands the other its record.
    record = create_or_get(
        db,
        lambda: DataInventoryRecord(
            data_inventory_row_id=row_id, status=DataInventoryStatus.DRAFT
        ),
        lambda: data_inventory_record_repository.get_for_row(db, row_id),
    )
    _write_status_to_row(db, row_id, record.status)
    return record


def list_records(db: Session) -> list[DataInventoryRecord]:
    return data_inventory_record_repository.list_all(db)


def approved_row_ids(db: Session) -> set[int]:
    """Rows whose dataset entry has been approved -- what the AI system's
    development-stage gate checks."""
    return {
        record.data_inventory_row_id
        for record in data_inventory_record_repository.list_all(db)
        if record.status == DataInventoryStatus.APPROVED
    }


def _write_status_to_row(db: Session, row_id: int, status: str) -> None:
    """Mirror the review status into the sheet cell so the grid and the xlsx
    export stay truthful. The cell is server-owned -- see update_row."""
    row = sheet_repository.get_row(db, row_id)
    if row is None:
        return
    row.data = {**row.data, STATUS_COLUMN_KEY: status}
    sheet_repository.save_row(db, row)


def unlink_ai_system(db: Session, ai_system_row_id: int, actor_id: int | None) -> list[SheetRow]:
    """Clears the AI System cell on every dataset pointing at a system that is
    being deleted, so the link doesn't dangle at a row that no longer exists.

    The dataset itself survives: it is an organizational data asset with its
    own Data Owner and review, and unlike an assessment it doesn't describe
    the system -- it just happened to be used by it.

    The approval is deliberately left standing. What the Data Owner signed off
    (what this data is, who owns it, how it was acquired and prepared) hasn't
    changed; a pointer to a deleted row is broken bookkeeping either way, and
    clearing it isn't the owner revising their dataset."""
    unlinked = []
    for row in list_rows(db):
        if str(row.data.get(AI_SYSTEM_COLUMN_KEY) or "").strip() != str(ai_system_row_id):
            continue
        row.data = {k: v for k, v in row.data.items() if k != AI_SYSTEM_COLUMN_KEY}
        unlinked.append(sheet_repository.save_row(db, row))
        audit_service.log(
            db, ENTITY_TYPE, get_or_create_sheet(db).id, "ai_system_unlinked", actor_id,
            {"row_id": row.id, "ai_system_row_id": ai_system_row_id},
        )
    return unlinked


# ---------- ownership ----------


def _owner_id(row: SheetRow) -> int | None:
    """The user id in the row's Data Owner cell, or None when it is unset or
    doesn't resolve to one -- parsed the same way dashboard_service counts
    owners that aren't real accounts."""
    raw = row.data.get(OWNER_COLUMN_KEY)
    if raw is None or not str(raw).strip():
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _require_data_owner(db: Session, row: SheetRow, actor_id: int | None) -> None:
    """Only the Data Owner named on a dataset may change it. No real actor
    (seed script / internal call) means nothing to enforce, mirroring
    governance_role_service.require_caigo; and a row nobody owns yet stays
    open to any editor, or there would be no way to fill one in and assign it.
    Admins are never locked out of their own inventory."""
    if actor_id is None:
        return
    owner_id = _owner_id(row)
    if owner_id is None or owner_id == actor_id:
        return
    actor = db.get(User, actor_id)
    if actor is not None and actor.role == UserRole.ADMIN:
        return
    raise AuthorizationError(
        "Only this dataset's Data Owner can change it."
    )


# ---------- rows ----------


def set_columns(db: Session, columns: list[ColumnDef], actor_id: int | None) -> Sheet:
    sheet = get_or_create_sheet(db)
    result = sheet_service.set_columns(db, sheet.id, columns)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "columns_updated", actor_id)
    return result


def add_row(db: Session, data: dict, actor_id: int | None) -> SheetRow:
    sheet = get_or_create_sheet(db)
    row = sheet_service.add_row(
        db, sheet.id, {k: v for k, v in data.items() if k != STATUS_COLUMN_KEY}
    )
    get_or_create_record(db, row.id)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "row_added", actor_id, {"row_id": row.id})
    return sheet_repository.get_row(db, row.id) or row


def update_row(db: Session, row_id: int, data: dict, actor_id: int | None) -> SheetRow:
    sheet = get_or_create_sheet(db)
    existing = _get_row_or_raise(db, row_id)
    _require_data_owner(db, existing, actor_id)

    # The status cell is server-owned -- editing it in the grid would sidestep
    # the review entirely, so a supplied value is ignored rather than rejected.
    changes = {k: v for k, v in data.items() if k != STATUS_COLUMN_KEY}
    changed = {**existing.data, **changes} != existing.data

    row = sheet_service.update_row(db, sheet.id, row_id, changes)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "row_updated", actor_id, {"row_id": row_id})
    if changed:
        _revert_review(db, row_id, actor_id)
    return sheet_repository.get_row(db, row_id) or row


def _claim(
    db: Session,
    record: DataInventoryRecord,
    expected: str,
    changes: dict,
    refusal: str,
) -> None:
    """The status check above ran in a transaction of its own, so a
    simultaneous caller can pass it too -- restating the expected status in
    the write is what makes only one of them land."""
    if not claim_transition(db, record, expected_statuses=expected, changes=changes):
        raise ConflictError(
            f"{refusal} -- someone else has already moved it on, and it is now "
            f"'{record.status}'."
        )


def _revert_review(db: Session, row_id: int, actor_id: int | None) -> None:
    """An edit invalidates whatever review the entry was in: an approval would
    otherwise describe data that has since changed, and a pending submission
    would put something different in front of the approver than what was
    submitted. Either way it goes back to draft and has to be re-submitted."""
    record = get_or_create_record(db, row_id)
    if record.status == DataInventoryStatus.DRAFT:
        return
    # Unguarded, and writing every field rather than assigning them: an
    # approval landing between the read above and this write still has to be
    # taken down, because it describes data that has since changed. See
    # concurrency.withdraw_transition.
    withdraw_transition(
        db,
        record,
        {
            "status": DataInventoryStatus.DRAFT,
            "submitted_by": None,
            "submitted_at": None,
            "approved_by": None,
            "approved_at": None,
        },
    )
    _write_status_to_row(db, row_id, record.status)
    audit_service.log(db, APPROVAL_ENTITY_TYPE, row_id, "review_reset_by_edit", actor_id)


def delete_row(db: Session, row_id: int, actor_id: int | None) -> None:
    sheet = get_or_create_sheet(db)
    row = _get_row_or_raise(db, row_id)
    _require_data_owner(db, row, actor_id)

    data_inventory_record_repository.delete_for_row(db, row_id)
    sheet_service.delete_row(db, sheet.id, row_id)
    audit_service.log(db, ENTITY_TYPE, sheet.id, "row_deleted", actor_id, {"row_id": row_id})


# ---------- review workflow ----------


def submit_for_approval(db: Session, row_id: int, actor_id: int | None) -> DataInventoryRecord:
    """The Data Owner puts their dataset entry forward for CAIGO sign-off."""
    row = _get_row_or_raise(db, row_id)
    record = get_or_create_record(db, row_id)
    if record.status != DataInventoryStatus.DRAFT:
        raise ConflictError(
            f"Dataset {row_id} must be draft to submit for approval, "
            f"currently '{record.status}'"
        )
    if _owner_id(row) is None:
        raise ValidationError(
            "This dataset has no Data Owner assigned yet -- assign one before "
            "submitting it for approval, so there is someone accountable for it."
        )
    if not str(row.data.get(NAME_COLUMN_KEY) or "").strip():
        raise ValidationError("Give the dataset a name before submitting it for approval.")
    _require_data_owner(db, row, actor_id)
    governance_role_service.require_a_possible_approver(db, actor_id)

    _claim(
        db,
        record,
        DataInventoryStatus.DRAFT,
        {
            "status": DataInventoryStatus.PENDING_APPROVAL,
            "submitted_by": actor_id,
            "submitted_at": datetime.now(UTC),
        },
        f"Dataset {row_id} is no longer draft",
    )
    _write_status_to_row(db, row_id, record.status)
    audit_service.log(db, APPROVAL_ENTITY_TYPE, row_id, "submitted_for_review", actor_id)
    return record


def approve(db: Session, row_id: int, actor_id: int | None) -> DataInventoryRecord:
    """CAIGO sign-off, by someone other than whoever submitted it."""
    _get_row_or_raise(db, row_id)
    record = get_or_create_record(db, row_id)
    if record.status != DataInventoryStatus.PENDING_APPROVAL:
        raise ConflictError(
            f"Dataset {row_id} must be pending approval to approve, "
            f"currently '{record.status}'"
        )

    governance_role_service.require_caigo(db, actor_id)
    try:
        audit_service.require_different_approver(db, APPROVAL_ENTITY_TYPE, row_id, actor_id)
    except ConflictError as exc:
        # The shared helper names the internal entity type, which means nothing
        # to whoever is looking at the data inventory grid.
        raise ConflictError(
            "You submitted this dataset, so someone else has to approve it."
        ) from exc

    _claim(
        db,
        record,
        DataInventoryStatus.PENDING_APPROVAL,
        {
            "status": DataInventoryStatus.APPROVED,
            "approved_by": actor_id,
            "approved_at": datetime.now(UTC),
        },
        f"Dataset {row_id} is no longer pending approval",
    )
    _write_status_to_row(db, row_id, record.status)
    audit_service.log(db, APPROVAL_ENTITY_TYPE, row_id, "approved", actor_id)
    return record


# ---------- import / export ----------


def export_xlsx(db: Session) -> bytes:
    sheet = get_or_create_sheet(db)
    return sheet_service.export_xlsx(db, sheet.id)


def import_upload(db: Session, file: UploadFile, actor_id: int | None) -> Sheet:
    """Matches rows to their existing dataset entry (by the file's ID column,
    falling back to dataset_name -- see sheet_service.import_upload), so a
    re-upload updates a dataset in place rather than losing its review to a
    reused row id. A matched row whose data actually changed still has to
    go back to draft, the same rule update_row already enforces for a
    single-row edit -- an approval describes the dataset as it stood when
    it was signed, and a bulk import is not an exception to that."""
    sheet = get_or_create_sheet(db)
    # sheet_service keeps the server-owned status column across the import.
    outcome = sheet_service.import_upload(
        db, sheet.id, file, natural_key_column=NAME_COLUMN_KEY
    )

    rows = sheet_service.list_rows(db, sheet.id)
    # Nothing is deleted by import any more, so this now only ever cleans up
    # a record left behind by something else -- kept as a harmless backstop.
    data_inventory_record_repository.delete_orphaned(db, {row.id for row in rows})
    for row in rows:
        record = get_or_create_record(db, row.id)
        if row.id in outcome.changed_row_ids:
            _revert_review(db, row.id, actor_id)
            record = get_or_create_record(db, row.id)
        # The import just wrote this row's data wholesale from the file,
        # which has no approval_status column of its own -- restamp the
        # cell from the record regardless of path, or a matched row that
        # didn't need reverting would show a blank status until something
        # else happened to touch it.
        _write_status_to_row(db, row.id, record.status)

    audit_service.log(db, ENTITY_TYPE, sheet.id, "sheet_uploaded", actor_id)
    return outcome.sheet
