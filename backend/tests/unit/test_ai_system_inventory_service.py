from unittest.mock import MagicMock, patch

import pytest

from app.models.sheet import Sheet
from app.services import ai_system_inventory_service


@pytest.fixture()
def db() -> MagicMock:
    return MagicMock()


@patch("app.services.ai_system_inventory_service.sheet_service")
@patch("app.services.ai_system_inventory_service.sheet_repository")
def test_get_or_create_sheet_creates_when_missing(mock_repo, mock_sheet_service, db) -> None:
    mock_repo.get_by_entity_type.return_value = None
    created = Sheet(id=1, entity_type="AISystemInventory", title="AI System Inventory", columns=[])
    mock_sheet_service.create_sheet.return_value = created

    result = ai_system_inventory_service.get_or_create_sheet(db)

    assert result is created
    mock_sheet_service.create_sheet.assert_called_once_with(
        db,
        "AISystemInventory",
        "AI System Inventory",
        ai_system_inventory_service.DEFAULT_COLUMNS,
    )


@patch("app.services.ai_system_inventory_service.sheet_service")
@patch("app.services.ai_system_inventory_service.sheet_repository")
def test_get_or_create_sheet_returns_existing(mock_repo, mock_sheet_service, db) -> None:
    existing = Sheet(id=1, entity_type="AISystemInventory", title="AI System Inventory", columns=[])
    mock_repo.get_by_entity_type.return_value = existing

    result = ai_system_inventory_service.get_or_create_sheet(db)

    assert result is existing
    mock_sheet_service.create_sheet.assert_not_called()
