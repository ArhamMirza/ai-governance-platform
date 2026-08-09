import io
from types import SimpleNamespace

import openpyxl
import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.schemas.sheet import ColumnDef
from app.services import sheet_service


def make_upload_file(filename: str, content: bytes):
    return SimpleNamespace(filename=filename, file=io.BytesIO(content))


def build_xlsx_bytes(headers: list[str], rows: list[list]) -> bytes:
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_import_csv_creates_columns_and_rows(db_session: Session) -> None:
    sheet = sheet_service.create_sheet(db_session, "RiskAssessment", "Risk Items", [])
    csv_content = b"Category,Likelihood\nBias,3\nPrivacy,5\n"
    upload = make_upload_file("risks.csv", csv_content)

    updated = sheet_service.import_upload(db_session, sheet.id, upload)

    assert [c["key"] for c in updated.columns] == ["category", "likelihood"]
    rows = sheet_service.list_rows(db_session, sheet.id)
    assert [r.data for r in rows] == [
        {"category": "Bias", "likelihood": "3"},
        {"category": "Privacy", "likelihood": "5"},
    ]


def test_import_xlsx_creates_columns_and_rows(db_session: Session) -> None:
    sheet = sheet_service.create_sheet(db_session, "RiskAssessment", "Risk Items", [])
    xlsx_content = build_xlsx_bytes(
        ["Category", "Likelihood"], [["Bias", 3], ["Privacy", 5]]
    )
    upload = make_upload_file("risks.xlsx", xlsx_content)

    updated = sheet_service.import_upload(db_session, sheet.id, upload)

    assert [c["key"] for c in updated.columns] == ["category", "likelihood"]
    rows = sheet_service.list_rows(db_session, sheet.id)
    assert [r.data for r in rows] == [
        {"category": "Bias", "likelihood": "3"},
        {"category": "Privacy", "likelihood": "5"},
    ]


def test_import_replaces_existing_columns_and_rows(db_session: Session) -> None:
    sheet = sheet_service.create_sheet(
        db_session, "RiskAssessment", "Risk Items", [ColumnDef(key="old", label="Old")]
    )
    sheet_service.add_row(db_session, sheet.id, {"old": "stale"})
    upload = make_upload_file("risks.csv", b"Category\nBias\n")

    sheet_service.import_upload(db_session, sheet.id, upload)

    rows = sheet_service.list_rows(db_session, sheet.id)
    assert len(rows) == 1
    assert rows[0].data == {"category": "Bias"}


def test_import_rejects_unsupported_file_type(db_session: Session) -> None:
    sheet = sheet_service.create_sheet(db_session, "RiskAssessment", "Risk Items", [])
    upload = make_upload_file("risks.txt", b"not a real sheet")

    with pytest.raises(ValidationError):
        sheet_service.import_upload(db_session, sheet.id, upload)


def test_import_deduplicates_repeated_headers(db_session: Session) -> None:
    sheet = sheet_service.create_sheet(db_session, "RiskAssessment", "Risk Items", [])
    upload = make_upload_file("risks.csv", b"Note,Note\nfirst,second\n")

    updated = sheet_service.import_upload(db_session, sheet.id, upload)

    assert [c["key"] for c in updated.columns] == ["note", "note_1"]


def test_export_xlsx_round_trips_rows(db_session: Session) -> None:
    sheet = sheet_service.create_sheet(
        db_session,
        "RiskAssessment",
        "Risk Items",
        [
            ColumnDef(key="category", label="Category"),
            ColumnDef(key="likelihood", label="Likelihood"),
        ],
    )
    sheet_service.add_row(db_session, sheet.id, {"category": "Bias", "likelihood": 3})

    exported = sheet_service.export_xlsx(db_session, sheet.id)

    workbook = openpyxl.load_workbook(io.BytesIO(exported))
    worksheet = workbook.active
    values = list(worksheet.iter_rows(values_only=True))
    assert values == [("Category", "Likelihood"), ("Bias", 3)]
