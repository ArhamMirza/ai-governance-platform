from sqlalchemy.orm import Session

from app.repositories import sheet_repository
from app.services import ai_system_inventory_service


def test_get_or_create_sheet_creates_when_missing(db_session: Session) -> None:
    assert sheet_repository.get_by_entity_type(db_session, "AISystemInventory") is None

    sheet = ai_system_inventory_service.get_or_create_sheet(db_session)

    assert sheet.entity_type == "AISystemInventory"
    assert sheet.title == "AI System Inventory"
    assert [column["key"] for column in sheet.columns] == [
        column.key for column in ai_system_inventory_service.DEFAULT_COLUMNS
    ]


def test_get_or_create_sheet_returns_existing(db_session: Session) -> None:
    first = ai_system_inventory_service.get_or_create_sheet(db_session)

    second = ai_system_inventory_service.get_or_create_sheet(db_session)

    assert second.id == first.id
