from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.sheet import Sheet, SheetRow


def get(db: Session, sheet_id: int) -> Sheet | None:
    return db.get(Sheet, sheet_id)


def get_by_entity_type(db: Session, entity_type: str) -> Sheet | None:
    return db.scalar(select(Sheet).where(Sheet.entity_type == entity_type))


def create(db: Session, sheet: Sheet) -> Sheet:
    db.add(sheet)
    db.commit()
    db.refresh(sheet)
    return sheet


def save(db: Session, sheet: Sheet) -> Sheet:
    db.commit()
    db.refresh(sheet)
    return sheet


def delete(db: Session, sheet: Sheet) -> None:
    db.delete(sheet)
    db.commit()


def get_row(db: Session, row_id: int) -> SheetRow | None:
    return db.get(SheetRow, row_id)


def list_rows(db: Session, sheet_id: int) -> list[SheetRow]:
    return list(
        db.scalars(
            select(SheetRow).where(SheetRow.sheet_id == sheet_id).order_by(SheetRow.row_index)
        )
    )


def next_row_index(db: Session, sheet_id: int) -> int:
    max_index = db.scalar(
        select(func.max(SheetRow.row_index)).where(SheetRow.sheet_id == sheet_id)
    )
    return (max_index or 0) + 1


def create_row(db: Session, row: SheetRow) -> SheetRow:
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def save_row(db: Session, row: SheetRow) -> SheetRow:
    db.commit()
    db.refresh(row)
    return row


def delete_row(db: Session, row: SheetRow) -> None:
    db.delete(row)
    db.commit()


def delete_all_rows(db: Session, sheet_id: int) -> None:
    for row in list_rows(db, sheet_id):
        db.delete(row)
    db.commit()
