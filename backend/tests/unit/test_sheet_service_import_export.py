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


def test_import_rejects_empty_csv_file(db_session: Session) -> None:
    sheet = sheet_service.create_sheet(db_session, "RiskAssessment", "Risk Items", [])
    upload = make_upload_file("risks.csv", b"")

    with pytest.raises(ValidationError):
        sheet_service.import_upload(db_session, sheet.id, upload)


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


def test_import_keeps_a_server_owned_column_the_file_omits(db_session: Session) -> None:
    """An uploaded file has no reason to carry lifecycle_stage, but the stage
    itself still exists -- dropping the column would leave it with nowhere to
    show and let a re-upload quietly undo the reserved-column guard."""
    sheet = sheet_service.create_sheet(
        db_session,
        "AISystemInventory",
        "AI Systems",
        [ColumnDef(key="name", label="Name"), ColumnDef(key="lifecycle_stage", label="Stage")],
    )
    upload = make_upload_file("systems.csv", b"Name\nResume Screener\n")

    updated = sheet_service.import_upload(db_session, sheet.id, upload)

    assert [c["key"] for c in updated.columns] == ["name", "lifecycle_stage"]
    # The label the app gave it survives too, rather than being regenerated.
    assert updated.columns[1]["label"] == "Stage"


def test_import_keeps_the_data_inventory_review_column(db_session: Session) -> None:
    sheet = sheet_service.create_sheet(
        db_session,
        "DataInventory",
        "Data Inventory",
        [
            ColumnDef(key="dataset_name", label="Dataset Name"),
            ColumnDef(key="approval_status", label="Approval Status"),
        ],
    )
    upload = make_upload_file("datasets.csv", b"Dataset Name\nApplicant CVs\n")

    updated = sheet_service.import_upload(db_session, sheet.id, upload)

    assert "approval_status" in {c["key"] for c in updated.columns}


def test_import_does_not_duplicate_a_server_owned_column_the_file_includes(
    db_session: Session,
) -> None:
    sheet = sheet_service.create_sheet(
        db_session,
        "AISystemInventory",
        "AI Systems",
        [ColumnDef(key="lifecycle_stage", label="Stage")],
    )
    upload = make_upload_file("systems.csv", b"Name,Lifecycle Stage\nResume Screener,design\n")

    updated = sheet_service.import_upload(db_session, sheet.id, upload)

    assert [c["key"] for c in updated.columns] == ["name", "lifecycle_stage"]


def test_import_does_not_invent_reserved_columns_the_sheet_never_had(
    db_session: Session,
) -> None:
    """Only a reserved column the sheet actually carries is preserved -- a risk
    sheet with no scoring columns doesn't grow them on import."""
    sheet = sheet_service.create_sheet(
        db_session, "RiskAssessment", "Risk Items", [ColumnDef(key="old", label="Old")]
    )
    upload = make_upload_file("risks.csv", b"Category\nBias\n")

    updated = sheet_service.import_upload(db_session, sheet.id, upload)

    assert [c["key"] for c in updated.columns] == ["category"]


def test_import_keeps_the_risk_scoring_columns(db_session: Session) -> None:
    sheet = sheet_service.create_sheet(
        db_session,
        "RiskAssessment",
        "Risk Items",
        [
            ColumnDef(key="category", label="Category"),
            ColumnDef(key="likelihood", label="Likelihood"),
            ColumnDef(key="impact", label="Impact"),
        ],
    )
    upload = make_upload_file("risks.csv", b"Category\nBias\n")

    updated = sheet_service.import_upload(db_session, sheet.id, upload)

    assert [c["key"] for c in updated.columns] == ["category", "likelihood", "impact"]


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
