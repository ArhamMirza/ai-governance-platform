import csv
import io
import re
from dataclasses import dataclass

import openpyxl
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.concurrency import create_or_get
from app.core.exceptions import NotFoundError, ValidationError
from app.models.sheet import Sheet, SheetRow
from app.repositories import sheet_repository
from app.schemas.sheet import ColumnDef

RISK_ASSESSMENT_ENTITY_TYPE = "RiskAssessment"

# Reserved risk-scoring inputs: once a RiskAssessment sheet has these columns,
# set_columns() refuses to drop them (see set_columns below).
RESERVED_RISK_INPUT_COLUMNS = {"likelihood", "impact", "residual_likelihood", "residual_impact"}

AI_SYSTEM_INVENTORY_ENTITY_TYPE = "AISystemInventory"

# lifecycle_stage is owned by the life cycle service and gated by stage gates,
# so it can't be dropped from the inventory sheet either.
RESERVED_AI_SYSTEM_COLUMNS = {"lifecycle_stage"}

DATA_INVENTORY_ENTITY_TYPE = "DataInventory"

# approval_status is owned by data_inventory_service and mirrors each dataset's
# review record, so it can't be dropped from the data inventory sheet.
RESERVED_DATA_INVENTORY_COLUMNS = {"approval_status"}

# entity type -> (what to call these columns in an error, the reserved keys).
# set_columns refuses to drop them and import_upload puts them back, so a
# server-owned column can't be lost by editing or re-uploading the sheet.
RESERVED_COLUMNS = {
    RISK_ASSESSMENT_ENTITY_TYPE: ("risk-scoring", RESERVED_RISK_INPUT_COLUMNS),
    AI_SYSTEM_INVENTORY_ENTITY_TYPE: ("life cycle", RESERVED_AI_SYSTEM_COLUMNS),
    DATA_INVENTORY_ENTITY_TYPE: ("review", RESERVED_DATA_INVENTORY_COLUMNS),
}


def _reserved_keys(entity_type: str) -> set[str]:
    return RESERVED_COLUMNS.get(entity_type, ("", set()))[1]

# score_key -> (likelihood_key, impact_key). Computed and overwritten on every
# add_row/update_row for a RiskAssessment sheet -- never taken from caller input.
SCORE_COLUMN_PAIRS = {
    "inherent_risk_score": ("likelihood", "impact"),
    "residual_risk_score": ("residual_likelihood", "residual_impact"),
}


def _to_number(value: object) -> float:
    if isinstance(value, bool):
        raise TypeError("booleans are not valid risk scoring inputs")
    if isinstance(value, int | float):
        return float(value)
    return float(str(value))


def _apply_computed_scores(entity_type: str, data: dict) -> dict:
    if entity_type != RISK_ASSESSMENT_ENTITY_TYPE:
        return data

    result = dict(data)
    for score_key, (likelihood_key, impact_key) in SCORE_COLUMN_PAIRS.items():
        result.pop(score_key, None)
        try:
            score = _to_number(result[likelihood_key]) * _to_number(result[impact_key])
        except (KeyError, TypeError, ValueError):
            continue
        result[score_key] = score
    return result


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


def get_or_create_singleton_sheet(
    db: Session, entity_type: str, title: str, columns: list[ColumnDef]
) -> Sheet:
    """The one sheet of its kind, provisioned on first use.

    Two simultaneous first requests would otherwise each provision their own
    -- the look-up and the insert are separate transactions, so neither sees
    the other's. Sheet.SINGLETON_ENTITY_TYPES carries the unique index that
    stops the second insert; the loser takes the winner's sheet, which is
    the sheet it was asking for."""
    existing = sheet_repository.get_by_entity_type(db, entity_type)
    if existing is not None:
        return existing
    return create_or_get(
        db,
        lambda: Sheet(
            entity_type=entity_type,
            title=title,
            columns=[column.model_dump() for column in columns],
        ),
        lambda: sheet_repository.get_by_entity_type(db, entity_type),
    )


def get_sheet(db: Session, sheet_id: int) -> Sheet:
    return _get_or_raise(db, sheet_id)


def set_columns(db: Session, sheet_id: int, columns: list[ColumnDef]) -> Sheet:
    sheet = _get_or_raise(db, sheet_id)
    keys = [column.key for column in columns]
    if len(keys) != len(set(keys)):
        raise ValidationError("Column keys must be unique")

    new_keys = set(keys)
    dropped_keys = _column_keys(sheet) - new_keys

    description, reserved = RESERVED_COLUMNS.get(sheet.entity_type, ("", set()))
    dropped_reserved = dropped_keys & reserved
    if dropped_reserved:
        raise ValidationError(
            f"Cannot remove reserved {description} column(s): "
            f"{', '.join(sorted(dropped_reserved))}"
        )
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
        data=_apply_computed_scores(sheet.entity_type, data),
    )
    return sheet_repository.create_row(db, row)


def update_row(db: Session, sheet_id: int, row_id: int, data: dict) -> SheetRow:
    sheet = _get_or_raise(db, sheet_id)
    row = _get_row_or_raise(db, sheet_id, row_id)
    _validate_row_keys(sheet, data)
    merged = {**row.data, **data}
    row.data = _apply_computed_scores(sheet.entity_type, merged)
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

    # A leading ID column, not part of sheet.columns -- see import_upload's
    # own comment. Re-uploading this same file lets import match each row
    # back to itself instead of recreating everything from scratch.
    headers = ["ID"] + [column["label"] for column in sheet.columns]
    keys = [column["key"] for column in sheet.columns]
    worksheet.append(headers)
    for row in rows:
        worksheet.append([row.id] + [row.data.get(key, "") for key in keys])

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


@dataclass
class ImportOutcome:
    """What import_upload actually did.

    changed_row_ids is populated only for rows matched to an existing one
    whose data genuinely differs from what was there before -- a caller
    that gates something on a row's content uses this to react the same
    way a single-row edit would. Data Inventory is the one that does:
    withdrawing that dataset's approval, the same rule update_row already
    enforces for a single-row edit."""

    sheet: Sheet
    changed_row_ids: set[int]


def _parse_row_id(value: str) -> int | None:
    """The exported ID column round-trips as plain text through CSV, but an
    xlsx cell can come back as an int or a float depending on how the file
    was saved -- "3" and "3.0" both mean row 3."""
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def import_upload(
    db: Session, sheet_id: int, file: UploadFile, natural_key_column: str | None = None
) -> ImportOutcome:
    """Reconciles the file against the sheet's existing rows rather than
    replacing them outright.

    Every row this sheet carries a lifecycle, an assessment, evidence or a
    review against is identified by its row id -- and a wholesale
    delete-then-recreate broke that identity on every re-upload (SQLite
    reuses a freed rowid, so a new row could silently inherit an old one's
    entire history). Matching by id -- falling back to natural_key_column
    for files that don't have the exported ID column at all -- keeps a
    matched row's id, and its state, attached to the right record. A row
    the file doesn't mention is left alone: import only adds and updates,
    it never removes (there's a dedicated delete action for that, which
    goes through the checks a bulk upload has no way to make -- e.g. an
    archived AI system's retention)."""
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

    # The ID column (see export_xlsx) is how a re-upload recognizes its own
    # rows. Pulled out before anything below ever sees it -- it must never
    # become a real, editable grid column.
    id_values: list[str] | None = None
    for column_index, header in enumerate(headers):
        if _slugify(header) == "id":
            id_values = [
                row[column_index] if column_index < len(row) else "" for row in data_rows
            ]
            headers = headers[:column_index] + headers[column_index + 1 :]
            data_rows = [
                row[:column_index] + row[column_index + 1 :] for row in data_rows
            ]
            break

    seen: dict[str, int] = {}
    keys = []
    for header in headers:
        base_key = _slugify(header)
        count = seen.get(base_key, 0)
        seen[base_key] = count + 1
        keys.append(base_key if count == 0 else f"{base_key}_{count}")

    columns = [
        ColumnDef(key=key, label=header).model_dump()
        for key, header in zip(keys, headers, strict=True)
    ]
    # The column list comes from the file, so a file that doesn't happen to
    # carry a server-owned column would otherwise drop it -- and the state
    # behind it (a life cycle stage, a dataset's review) would still exist
    # with nowhere to show. Those columns are kept regardless of the upload.
    imported_keys = {column["key"] for column in columns}
    reserved = _reserved_keys(sheet.entity_type)
    columns += [
        column
        for column in sheet.columns
        if column["key"] in reserved and column["key"] not in imported_keys
    ]

    sheet.columns = columns
    sheet_repository.save(db, sheet)

    existing = sheet_repository.list_rows(db, sheet_id)
    by_id: dict[int, SheetRow] = {row.id: row for row in existing}
    by_name: dict[str, SheetRow] = {}
    if natural_key_column is not None and natural_key_column in keys:
        for row in existing:
            name = str(row.data.get(natural_key_column) or "").strip().casefold()
            if name:
                by_name[name] = row

    def _consume(row: SheetRow) -> None:
        by_id.pop(row.id, None)
        if natural_key_column is not None:
            name = str(row.data.get(natural_key_column) or "").strip().casefold()
            by_name.pop(name, None)

    changed_row_ids: set[int] = set()
    for index, values in enumerate(data_rows, start=1):
        # Ragged CSV/xlsx rows are tolerated -- extra/missing cells just mean
        # extra/missing keys in that row's data, not a hard error.
        row_data = {key: value for key, value in zip(keys, values, strict=False) if value != ""}
        row_data = _apply_computed_scores(sheet.entity_type, row_data)

        match: SheetRow | None = None
        if id_values is not None:
            candidate_id = _parse_row_id(id_values[index - 1])
            if candidate_id is not None:
                match = by_id.get(candidate_id)
        if match is None and natural_key_column is not None:
            name = str(row_data.get(natural_key_column) or "").strip().casefold()
            if name:
                match = by_name.get(name)

        if match is not None:
            # Consumed regardless of which lookup found it, so a later file
            # row can't also claim it through the other one.
            _consume(match)
            # Compared against what row_data would look like merged onto the
            # row's own data, not against it raw: a server-owned cell (an
            # approval status, a life cycle stage) lives in match.data but
            # is never part of row_data -- the file has no reason to carry
            # it -- so a raw comparison would call every previously-reviewed
            # row "changed" on every import, whether or not anything the
            # file actually controls did.
            if {**match.data, **row_data} != match.data:
                changed_row_ids.add(match.id)
            match.row_index = index
            match.data = row_data
            sheet_repository.save_row(db, match)
        else:
            sheet_repository.create_row(
                db, SheetRow(sheet_id=sheet_id, row_index=index, data=row_data)
            )

    return ImportOutcome(sheet=sheet, changed_row_ids=changed_row_ids)
