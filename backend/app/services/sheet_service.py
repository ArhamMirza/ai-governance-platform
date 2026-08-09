import csv
import io
import re

import openpyxl
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.sheet import Sheet, SheetRow
from app.repositories import sheet_repository
from app.schemas.sheet import ColumnDef


def _get_or_raise(db: Session, sheet_id: int) -> Sheet:
    sheet = sheet_repository.get(db, sheet_id)
    if sheet is None:
        raise NotFoundError("Sheet", sheet_id)
    return sheet


def _get_row_or_raise(db: Session, sheet_id: int, row_id: int) -> SheetRow:
    row = sheet_repository.get_row(db, row_id)
    if row is None or row.sheet_id != sheet_id:
        raise NotFoundError("SheetRow", row_id)
    return row


def _column_keys(sheet: Sheet) -> set[str]:
    return {column["key"] for column in sheet.columns}


def _validate_row_keys(sheet: Sheet, data: dict) -> None:
    unknown = set(data.keys()) - _column_keys(sheet)
    if unknown:
        raise ValidationError(f"Unknown column(s) for this sheet: {', '.join(sorted(unknown))}")


def create_sheet(db: Session, entity_type: str, title: str, columns: list[ColumnDef]) -> Sheet:
    sheet = Sheet(
        entity_type=entity_type,
        title=title,
        columns=[column.model_dump() for column in columns],
    )
    return sheet_repository.create(db, sheet)


def get_sheet(db: Session, sheet_id: int) -> Sheet:
    return _get_or_raise(db, sheet_id)


def set_columns(db: Session, sheet_id: int, columns: list[ColumnDef]) -> Sheet:
    sheet = _get_or_raise(db, sheet_id)
    keys = [column.key for column in columns]
    if len(keys) != len(set(keys)):
        raise ValidationError("Column keys must be unique")

    new_keys = set(keys)
    dropped_keys = _column_keys(sheet) - new_keys
    if dropped_keys:
        for row in sheet_repository.list_rows(db, sheet_id):
            if dropped_keys & row.data.keys():
                row.data = {k: v for k, v in row.data.items() if k not in dropped_keys}
                sheet_repository.save_row(db, row)

    sheet.columns = [column.model_dump() for column in columns]
    return sheet_repository.save(db, sheet)


def list_rows(db: Session, sheet_id: int) -> list[SheetRow]:
    _get_or_raise(db, sheet_id)
    return sheet_repository.list_rows(db, sheet_id)


def add_row(db: Session, sheet_id: int, data: dict) -> SheetRow:
    sheet = _get_or_raise(db, sheet_id)
    _validate_row_keys(sheet, data)
    row = SheetRow(
        sheet_id=sheet_id,
        row_index=sheet_repository.next_row_index(db, sheet_id),
        data=data,
    )
    return sheet_repository.create_row(db, row)


def update_row(db: Session, sheet_id: int, row_id: int, data: dict) -> SheetRow:
    sheet = _get_or_raise(db, sheet_id)
    row = _get_row_or_raise(db, sheet_id, row_id)
    _validate_row_keys(sheet, data)
    row.data = {**row.data, **data}
    return sheet_repository.save_row(db, row)


def delete_row(db: Session, sheet_id: int, row_id: int) -> None:
    _get_or_raise(db, sheet_id)
    row = _get_row_or_raise(db, sheet_id, row_id)
    sheet_repository.delete_row(db, row)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return slug or "column"


def export_xlsx(db: Session, sheet_id: int) -> bytes:
    sheet = _get_or_raise(db, sheet_id)
    rows = sheet_repository.list_rows(db, sheet_id)

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = sheet.title[:31] or "Sheet"

    headers = [column["label"] for column in sheet.columns]
    keys = [column["key"] for column in sheet.columns]
    worksheet.append(headers)
    for row in rows:
        worksheet.append([row.data.get(key, "") for key in keys])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _parse_csv(contents: bytes) -> tuple[list[str], list[list[str]]]:
    text = contents.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _parse_xlsx(contents: bytes) -> tuple[list[str], list[list[str]]]:
    workbook = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
    worksheet = workbook.active
    values = [list(row) for row in worksheet.iter_rows(values_only=True)]
    if not values:
        return [], []
    headers = [str(cell) if cell is not None else "" for cell in values[0]]
    data_rows = [
        [str(cell) if cell is not None else "" for cell in row] for row in values[1:]
    ]
    return headers, data_rows


def import_upload(db: Session, sheet_id: int, file: UploadFile) -> Sheet:
    sheet = _get_or_raise(db, sheet_id)
    filename = file.filename or ""
    contents = file.file.read()

    if filename.lower().endswith(".csv"):
        headers, data_rows = _parse_csv(contents)
    elif filename.lower().endswith(".xlsx"):
        headers, data_rows = _parse_xlsx(contents)
    else:
        raise ValidationError("Only .csv and .xlsx files are supported")

    if not headers:
        raise ValidationError("File has no header row")

    seen: dict[str, int] = {}
    keys = []
    for header in headers:
        base_key = _slugify(header)
        count = seen.get(base_key, 0)
        seen[base_key] = count + 1
        keys.append(base_key if count == 0 else f"{base_key}_{count}")

    sheet.columns = [
        ColumnDef(key=key, label=header).model_dump()
        for key, header in zip(keys, headers, strict=True)
    ]
    sheet_repository.save(db, sheet)

    sheet_repository.delete_all_rows(db, sheet_id)
    for index, values in enumerate(data_rows, start=1):
        # Ragged CSV/xlsx rows are tolerated -- extra/missing cells just mean
        # extra/missing keys in that row's data, not a hard error.
        row_data = {key: value for key, value in zip(keys, values, strict=False) if value != ""}
        sheet_repository.create_row(
            db, SheetRow(sheet_id=sheet_id, row_index=index, data=row_data)
        )

    return sheet
