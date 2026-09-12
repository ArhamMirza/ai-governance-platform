from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.data_inventory_record import DataInventoryRecord


def get_for_row(db: Session, data_inventory_row_id: int) -> DataInventoryRecord | None:
    return db.scalar(
        select(DataInventoryRecord).where(
            DataInventoryRecord.data_inventory_row_id == data_inventory_row_id
        )
    )


def list_all(db: Session) -> list[DataInventoryRecord]:
    return list(db.scalars(select(DataInventoryRecord).order_by(DataInventoryRecord.id)))


def create(db: Session, record: DataInventoryRecord) -> DataInventoryRecord:
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def save(db: Session, record: DataInventoryRecord) -> DataInventoryRecord:
    db.commit()
    db.refresh(record)
    return record


def delete_for_row(db: Session, data_inventory_row_id: int) -> None:
    record = get_for_row(db, data_inventory_row_id)
    if record is not None:
        db.delete(record)
        db.commit()


def delete_orphaned(db: Session, live_row_ids: set[int]) -> None:
    """Drops records whose sheet row no longer exists -- an xlsx import
    replaces every row wholesale (see sheet_service.import_upload), so without
    this the table would accumulate records pointing at deleted rows."""
    stale = [
        record
        for record in list_all(db)
        if record.data_inventory_row_id not in live_row_ids
    ]
    for record in stale:
        db.delete(record)
    if stale:
        db.commit()
