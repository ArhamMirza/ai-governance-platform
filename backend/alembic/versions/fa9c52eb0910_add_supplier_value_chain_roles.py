"""add supplier value chain roles

Revision ID: fa9c52eb0910
Revises: 0d4a05040326
Create Date: 2026-10-02 22:55:37.451731

Records each supplier's EU AI Act role for every AI system it contributes
to, and the organization's Art. 25(1) triggers for that system. The three
triggers default to false on existing links (server_default), so the
NOT NULL columns can be added to a table that already has rows.

Also adds the Supplier column to every existing risk assessment's sheet --
new ones get it from risk_assessment_service.DEFAULT_COLUMNS -- placed
after Risk Owner, the same backfill pattern as migration 1b5d8bf92739.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fa9c52eb0910"
down_revision: str | Sequence[str] | None = "0d4a05040326"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SUPPLIER_COLUMN = {"key": "supplier_id", "label": "Supplier", "data_type": "text"}
_TRIGGERS = ("rebranded", "substantially_modified", "repurposed_to_high_risk")


def _sheets_table() -> sa.Table:
    return sa.table(
        "sheets",
        sa.column("id", sa.Integer),
        sa.column("entity_type", sa.String),
        sa.column("columns", sa.JSON),
    )


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("supplier_ai_systems") as batch:
        batch.add_column(sa.Column("supplier_role", sa.String(length=30), nullable=True))
        for name in _TRIGGERS:
            batch.add_column(
                sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false())
            )

    conn = op.get_bind()
    sheets = _sheets_table()
    for sheet in conn.execute(
        sa.select(sheets.c.id, sheets.c.columns).where(sheets.c.entity_type == "RiskAssessment")
    ).all():
        columns = list(sheet.columns or [])
        if any(column.get("key") == SUPPLIER_COLUMN["key"] for column in columns):
            continue
        owner_index = next(
            (i for i, column in enumerate(columns) if column.get("key") == "risk_owner"),
            len(columns) - 1,
        )
        columns.insert(owner_index + 1, SUPPLIER_COLUMN)
        conn.execute(sheets.update().where(sheets.c.id == sheet.id).values(columns=columns))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    sheets = _sheets_table()
    for sheet in conn.execute(
        sa.select(sheets.c.id, sheets.c.columns).where(sheets.c.entity_type == "RiskAssessment")
    ).all():
        columns = [c for c in (sheet.columns or []) if c.get("key") != SUPPLIER_COLUMN["key"]]
        conn.execute(sheets.update().where(sheets.c.id == sheet.id).values(columns=columns))

    with op.batch_alter_table("supplier_ai_systems") as batch:
        for name in reversed(_TRIGGERS):
            batch.drop_column(name)
        batch.drop_column("supplier_role")
