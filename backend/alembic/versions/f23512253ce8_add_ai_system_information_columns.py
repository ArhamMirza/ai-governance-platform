"""add ai system information columns

Revision ID: f23512253ce8
Revises: b2e8ecde5df9
Create Date: 2026-10-13 22:26:19.307020

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f23512253ce8"
down_revision: str | Sequence[str] | None = "b2e8ecde5df9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen here rather than imported from ai_system_inventory_service, so a
# later change to DEFAULT_COLUMNS can't change what this migration did.
NEW_COLUMNS = [
    {"key": "event_logging", "label": "Event Logging", "data_type": "text"},
    {"key": "log_retention", "label": "Log Retention", "data_type": "text"},
    {"key": "user_information", "label": "Information for Users", "data_type": "text"},
    {"key": "customer_information", "label": "Information for Customers", "data_type": "text"},
]

sheets_table = sa.table(
    "sheets",
    sa.column("id", sa.Integer),
    sa.column("entity_type", sa.String),
    sa.column("columns", sa.JSON),
)


def _inventory_sheet(conn):
    return conn.execute(
        sa.select(sheets_table.c.id, sheets_table.c.columns).where(
            sheets_table.c.entity_type == "AISystemInventory"
        )
    ).first()


def _set_columns(conn, sheet_id: int, columns: list[dict]) -> None:
    conn.execute(sheets_table.update().where(sheets_table.c.id == sheet_id).values(columns=columns))


def upgrade() -> None:
    """Append the A.6.2.8 / A.8.2 / A.10.4 columns to an already-provisioned
    AI System Inventory sheet. A fresh install gets them from DEFAULT_COLUMNS
    on first use."""
    conn = op.get_bind()
    sheet = _inventory_sheet(conn)
    if sheet is None:
        return
    existing_keys = {column["key"] for column in sheet.columns}
    missing = [column for column in NEW_COLUMNS if column["key"] not in existing_keys]
    if missing:
        _set_columns(conn, sheet.id, list(sheet.columns) + missing)


def downgrade() -> None:
    """Drop the columns from the sheet's definition. Values already typed into
    rows are left in the row data, so upgrading again shows them."""
    conn = op.get_bind()
    sheet = _inventory_sheet(conn)
    if sheet is None:
        return
    keys = {column["key"] for column in NEW_COLUMNS}
    _set_columns(conn, sheet.id, [c for c in sheet.columns if c["key"] not in keys])
