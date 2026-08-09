from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.models.sheet import Sheet, SheetRow
from app.schemas.sheet import ColumnDef
from app.services import sheet_service


def make_sheet(**overrides) -> Sheet:
    defaults = dict(
        id=1,
        entity_type="RiskAssessment",
        title="Risk Items",
        columns=[
            {"key": "category", "label": "Category", "data_type": "text"},
            {"key": "likelihood", "label": "Likelihood", "data_type": "number"},
        ],
    )
    defaults.update(overrides)
    return Sheet(**defaults)


def make_row(**overrides) -> SheetRow:
    defaults = dict(id=1, sheet_id=1, row_index=1, data={"category": "Bias"})
    defaults.update(overrides)
    return SheetRow(**defaults)


@pytest.fixture()
def db() -> MagicMock:
    return MagicMock()


@patch("app.services.sheet_service.sheet_repository")
def test_create_sheet(mock_repo, db) -> None:
    mock_repo.create.side_effect = lambda _db, sheet: sheet

    result = sheet_service.create_sheet(
        db, "RiskAssessment", "Risk Items", [ColumnDef(key="category", label="Category")]
    )

    assert result.entity_type == "RiskAssessment"
    assert result.columns == [{"key": "category", "label": "Category", "data_type": "text"}]


@patch("app.services.sheet_service.sheet_repository")
def test_get_sheet_raises_not_found(mock_repo, db) -> None:
    mock_repo.get.return_value = None

    with pytest.raises(NotFoundError):
        sheet_service.get_sheet(db, 999)


@patch("app.services.sheet_service.sheet_repository")
def test_set_columns_rejects_duplicate_keys(mock_repo, db) -> None:
    sheet = make_sheet()
    mock_repo.get.return_value = sheet

    with pytest.raises(ValidationError):
        sheet_service.set_columns(
            db,
            1,
            [ColumnDef(key="category", label="A"), ColumnDef(key="category", label="B")],
        )


@patch("app.services.sheet_service.sheet_repository")
def test_set_columns_strips_dropped_keys_from_existing_rows(mock_repo, db) -> None:
    sheet = make_sheet()
    row = make_row(data={"category": "Bias", "likelihood": 3})
    mock_repo.get.return_value = sheet
    mock_repo.list_rows.return_value = [row]
    mock_repo.save.side_effect = lambda _db, s: s
    mock_repo.save_row.side_effect = lambda _db, r: r

    sheet_service.set_columns(db, 1, [ColumnDef(key="category", label="Category")])

    assert row.data == {"category": "Bias"}
    assert sheet.columns == [{"key": "category", "label": "Category", "data_type": "text"}]


@patch("app.services.sheet_service.sheet_repository")
def test_add_row_accepts_known_columns(mock_repo, db) -> None:
    sheet = make_sheet()
    mock_repo.get.return_value = sheet
    mock_repo.next_row_index.return_value = 1
    mock_repo.create_row.side_effect = lambda _db, row: row

    result = sheet_service.add_row(db, 1, {"category": "Bias", "likelihood": 3})

    assert result.data == {"category": "Bias", "likelihood": 3}
    assert result.row_index == 1


@patch("app.services.sheet_service.sheet_repository")
def test_add_row_rejects_unknown_column(mock_repo, db) -> None:
    sheet = make_sheet()
    mock_repo.get.return_value = sheet

    with pytest.raises(ValidationError):
        sheet_service.add_row(db, 1, {"not_a_real_column": "x"})


@patch("app.services.sheet_service.sheet_repository")
def test_update_row_merges_data(mock_repo, db) -> None:
    sheet = make_sheet()
    row = make_row(data={"category": "Bias"})
    mock_repo.get.return_value = sheet
    mock_repo.get_row.return_value = row
    mock_repo.save_row.side_effect = lambda _db, r: r

    result = sheet_service.update_row(db, 1, 1, {"likelihood": 4})

    assert result.data == {"category": "Bias", "likelihood": 4}


@patch("app.services.sheet_service.sheet_repository")
def test_update_row_raises_not_found_for_wrong_sheet(mock_repo, db) -> None:
    sheet = make_sheet()
    row = make_row(sheet_id=999)
    mock_repo.get.return_value = sheet
    mock_repo.get_row.return_value = row

    with pytest.raises(NotFoundError):
        sheet_service.update_row(db, 1, 1, {"category": "x"})


@patch("app.services.sheet_service.sheet_repository")
def test_delete_row(mock_repo, db) -> None:
    sheet = make_sheet()
    row = make_row()
    mock_repo.get.return_value = sheet
    mock_repo.get_row.return_value = row

    sheet_service.delete_row(db, 1, 1)

    mock_repo.delete_row.assert_called_once_with(db, row)


@patch("app.services.sheet_service.sheet_repository")
def test_list_rows_raises_not_found_for_missing_sheet(mock_repo, db) -> None:
    mock_repo.get.return_value = None

    with pytest.raises(NotFoundError):
        sheet_service.list_rows(db, 999)
