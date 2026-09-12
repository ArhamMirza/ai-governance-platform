"""The Data Inventory review: the assigned Data Owner fills a dataset in and
submits it, the Chief AI Governance Officer approves it."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.governance_role_seed_data import DEFAULT_ROLES
from app.models.data_inventory_record import DataInventoryStatus
from app.models.governance_role import GovernanceRole
from app.models.user import UserRole
from app.schemas.sheet import ColumnDef
from app.services import data_inventory_service, governance_role_service


def make_dataset(db: Session, owner_id: int | None = None, name: str = "Resume corpus"):
    data = {"dataset_name": name}
    if owner_id is not None:
        data["data_owner"] = str(owner_id)
    return data_inventory_service.add_row(db, data, actor_id=None)


def make_caigo(db: Session, make_user):
    admin = make_user(role=UserRole.ADMIN)
    role = db.query(GovernanceRole).filter_by(name=DEFAULT_ROLES[0][0]).one()
    governance_role_service.assign_user(db, role.id, admin.id, actor_id=None)
    return admin


def submitted_dataset(db: Session, make_user):
    owner = make_user()
    row = make_dataset(db, owner_id=owner.id)
    data_inventory_service.submit_for_approval(db, row.id, actor_id=owner.id)
    return row, owner


def test_a_new_dataset_starts_in_draft_with_the_status_mirrored(db_session: Session) -> None:
    row = make_dataset(db_session)

    record = data_inventory_service.get_or_create_record(db_session, row.id)

    assert record.status == DataInventoryStatus.DRAFT
    assert row.data["approval_status"] == DataInventoryStatus.DRAFT


def test_an_unowned_dataset_stays_editable_by_anyone(db_session: Session, make_user) -> None:
    row = make_dataset(db_session)
    someone = make_user()

    updated = data_inventory_service.update_row(
        db_session, row.id, {"data_type": "training"}, actor_id=someone.id
    )

    assert updated.data["data_type"] == "training"


def test_only_the_assigned_data_owner_can_edit(db_session: Session, make_user) -> None:
    owner = make_user()
    other = make_user(role=UserRole.CONTRIBUTOR)
    row = make_dataset(db_session, owner_id=owner.id)

    with pytest.raises(AuthorizationError):
        data_inventory_service.update_row(
            db_session, row.id, {"data_type": "training"}, actor_id=other.id
        )

    data_inventory_service.update_row(
        db_session, row.id, {"data_type": "training"}, actor_id=owner.id
    )


def test_an_admin_can_edit_someone_elses_dataset(db_session: Session, make_user) -> None:
    owner = make_user(role=UserRole.CONTRIBUTOR)
    admin = make_user(role=UserRole.ADMIN)
    row = make_dataset(db_session, owner_id=owner.id)

    updated = data_inventory_service.update_row(
        db_session, row.id, {"data_type": "training"}, actor_id=admin.id
    )

    assert updated.data["data_type"] == "training"


def test_only_the_assigned_data_owner_can_delete(db_session: Session, make_user) -> None:
    owner = make_user()
    other = make_user(role=UserRole.CONTRIBUTOR)
    row = make_dataset(db_session, owner_id=owner.id)

    with pytest.raises(AuthorizationError):
        data_inventory_service.delete_row(db_session, row.id, actor_id=other.id)


def test_the_status_cell_cannot_be_set_from_the_grid(db_session: Session) -> None:
    row = make_dataset(db_session)

    updated = data_inventory_service.update_row(
        db_session, row.id, {"approval_status": "approved"}, actor_id=None
    )

    assert updated.data["approval_status"] == DataInventoryStatus.DRAFT


def test_the_status_column_cannot_be_dropped(db_session: Session) -> None:
    keep = [c for c in data_inventory_service.DEFAULT_COLUMNS if c.key != "approval_status"]

    with pytest.raises(ValidationError):
        data_inventory_service.set_columns(db_session, keep, actor_id=None)


def test_submitting_requires_a_data_owner(db_session: Session) -> None:
    row = make_dataset(db_session)

    with pytest.raises(ValidationError):
        data_inventory_service.submit_for_approval(db_session, row.id, actor_id=None)


def test_submitting_requires_a_dataset_name(db_session: Session, make_user) -> None:
    owner = make_user()
    row = make_dataset(db_session, owner_id=owner.id, name="")

    with pytest.raises(ValidationError):
        data_inventory_service.submit_for_approval(db_session, row.id, actor_id=owner.id)


def test_only_the_data_owner_can_submit(db_session: Session, make_user) -> None:
    owner = make_user()
    other = make_user(role=UserRole.CONTRIBUTOR)
    row = make_dataset(db_session, owner_id=owner.id)

    with pytest.raises(AuthorizationError):
        data_inventory_service.submit_for_approval(db_session, row.id, actor_id=other.id)


def test_submitting_moves_it_to_pending_approval(db_session: Session, make_user) -> None:
    row, owner = submitted_dataset(db_session, make_user)

    record = data_inventory_service.get_or_create_record(db_session, row.id)
    assert record.status == DataInventoryStatus.PENDING_APPROVAL
    assert record.submitted_by == owner.id


def test_cannot_submit_twice(db_session: Session, make_user) -> None:
    row, owner = submitted_dataset(db_session, make_user)

    with pytest.raises(ConflictError):
        data_inventory_service.submit_for_approval(db_session, row.id, actor_id=owner.id)


def test_approving_requires_caigo(db_session: Session, make_user) -> None:
    row, _ = submitted_dataset(db_session, make_user)
    not_caigo = make_user(role=UserRole.ADMIN)

    with pytest.raises(AuthorizationError):
        data_inventory_service.approve(db_session, row.id, actor_id=not_caigo.id)


def test_caigo_cannot_approve_their_own_submission(db_session: Session, make_user) -> None:
    caigo = make_caigo(db_session, make_user)
    row = make_dataset(db_session, owner_id=caigo.id)
    data_inventory_service.submit_for_approval(db_session, row.id, actor_id=caigo.id)

    with pytest.raises(ConflictError):
        data_inventory_service.approve(db_session, row.id, actor_id=caigo.id)


def test_caigo_approval_stamps_the_approver(db_session: Session, make_user) -> None:
    row, _ = submitted_dataset(db_session, make_user)
    caigo = make_caigo(db_session, make_user)

    record = data_inventory_service.approve(db_session, row.id, actor_id=caigo.id)

    assert record.status == DataInventoryStatus.APPROVED
    assert record.approved_by == caigo.id
    assert data_inventory_service.approved_row_ids(db_session) == {row.id}


def test_cannot_approve_a_draft(db_session: Session, make_user) -> None:
    row = make_dataset(db_session)
    caigo = make_caigo(db_session, make_user)

    with pytest.raises(ConflictError):
        data_inventory_service.approve(db_session, row.id, actor_id=caigo.id)


def test_editing_an_approved_dataset_sends_it_back_to_draft(
    db_session: Session, make_user
) -> None:
    row, owner = submitted_dataset(db_session, make_user)
    caigo = make_caigo(db_session, make_user)
    data_inventory_service.approve(db_session, row.id, actor_id=caigo.id)

    updated = data_inventory_service.update_row(
        db_session, row.id, {"data_source": "Applicant portal"}, actor_id=owner.id
    )

    record = data_inventory_service.get_or_create_record(db_session, row.id)
    assert record.status == DataInventoryStatus.DRAFT
    assert record.approved_by is None and record.submitted_by is None
    assert updated.data["approval_status"] == DataInventoryStatus.DRAFT
    assert data_inventory_service.approved_row_ids(db_session) == set()


def test_editing_a_pending_dataset_sends_it_back_to_draft(
    db_session: Session, make_user
) -> None:
    """The approver would otherwise be shown something other than what was
    actually submitted."""
    row, owner = submitted_dataset(db_session, make_user)

    data_inventory_service.update_row(
        db_session, row.id, {"data_source": "Applicant portal"}, actor_id=owner.id
    )

    record = data_inventory_service.get_or_create_record(db_session, row.id)
    assert record.status == DataInventoryStatus.DRAFT


def test_an_edit_that_changes_nothing_keeps_the_approval(
    db_session: Session, make_user
) -> None:
    row, owner = submitted_dataset(db_session, make_user)
    caigo = make_caigo(db_session, make_user)
    data_inventory_service.approve(db_session, row.id, actor_id=caigo.id)

    data_inventory_service.update_row(
        db_session, row.id, {"dataset_name": "Resume corpus"}, actor_id=owner.id
    )

    record = data_inventory_service.get_or_create_record(db_session, row.id)
    assert record.status == DataInventoryStatus.APPROVED


def test_deleting_a_dataset_removes_its_record(db_session: Session) -> None:
    row = make_dataset(db_session)
    data_inventory_service.get_or_create_record(db_session, row.id)

    data_inventory_service.delete_row(db_session, row.id, actor_id=None)

    assert data_inventory_service.list_records(db_session) == []
    with pytest.raises(NotFoundError):
        data_inventory_service.get_or_create_record(db_session, row.id)


def test_importing_replaces_the_records_along_with_the_rows(db_session: Session) -> None:
    """An import wipes every row, so the old records have to go with them
    rather than being left pointing at rows that no longer exist."""
    old = make_dataset(db_session)
    data_inventory_service.get_or_create_record(db_session, old.id)

    csv = b"Dataset Name,Data Type\nApplicant CVs,training\n"
    data_inventory_service.import_upload(db_session, _upload(csv, "data.csv"), actor_id=None)

    rows = data_inventory_service.list_rows(db_session)
    records = data_inventory_service.list_records(db_session)
    assert [r.data_inventory_row_id for r in records] == [row.id for row in rows]
    assert all(record.status == DataInventoryStatus.DRAFT for record in records)


def test_importing_keeps_the_server_owned_status_column(db_session: Session) -> None:
    csv = b"Dataset Name,Data Type\nApplicant CVs,training\n"

    sheet = data_inventory_service.import_upload(
        db_session, _upload(csv, "data.csv"), actor_id=None
    )

    assert "approval_status" in {column["key"] for column in sheet.columns}


def _upload(content: bytes, filename: str):
    from io import BytesIO

    from fastapi import UploadFile

    return UploadFile(filename=filename, file=BytesIO(content))


def test_columns_can_still_be_renamed_around_the_reserved_one(db_session: Session) -> None:
    columns = [
        ColumnDef(key=c.key, label=f"{c.label}!") for c in data_inventory_service.DEFAULT_COLUMNS
    ]

    sheet = data_inventory_service.set_columns(db_session, columns, actor_id=None)

    assert sheet.columns[0]["label"] == "Dataset Name!"
