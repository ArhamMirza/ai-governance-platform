"""add data inventory records

Revision ID: 1b5d8bf92739
Revises: 2ff8e382653f
Create Date: 2026-09-12 00:00:00.000000

"""
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1b5d8bf92739'
down_revision: str | Sequence[str] | None = '2ff8e382653f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUS_COLUMN = {'key': 'approval_status', 'label': 'Approval Status', 'data_type': 'text'}


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('data_inventory_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('data_inventory_row_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('submitted_by', sa.Integer(), nullable=True),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('approved_by', sa.Integer(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['data_inventory_row_id'], ['sheet_rows.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_inventory_records_data_inventory_row_id'), 'data_inventory_records', ['data_inventory_row_id'], unique=True)

    # Every existing dataset entry starts its review at draft: nothing recorded
    # before this migration was ever reviewed, and claiming otherwise would
    # let unreviewed rows satisfy the AI system's data gate.
    conn = op.get_bind()
    sheets = sa.table(
        'sheets',
        sa.column('id', sa.Integer),
        sa.column('entity_type', sa.String),
        sa.column('columns', sa.JSON),
    )
    sheet_rows = sa.table(
        'sheet_rows',
        sa.column('id', sa.Integer),
        sa.column('sheet_id', sa.Integer),
        sa.column('data', sa.JSON),
    )
    records = sa.table(
        'data_inventory_records',
        sa.column('data_inventory_row_id', sa.Integer),
        sa.column('status', sa.String),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )

    sheet = conn.execute(
        sa.select(sheets.c.id, sheets.c.columns).where(
            sheets.c.entity_type == 'DataInventory'
        )
    ).first()
    if sheet is None:
        return

    # The status cell is server-owned, so the sheet needs the column to show it.
    columns = list(sheet.columns or [])
    if not any(column.get('key') == STATUS_COLUMN['key'] for column in columns):
        conn.execute(
            sheets.update()
            .where(sheets.c.id == sheet.id)
            .values(columns=[*columns, STATUS_COLUMN])
        )

    now = datetime.now(UTC)
    rows = conn.execute(
        sa.select(sheet_rows.c.id).where(sheet_rows.c.sheet_id == sheet.id)
    ).all()
    if not rows:
        return

    op.bulk_insert(
        records,
        [
            {
                'data_inventory_row_id': row.id,
                'status': 'draft',
                'created_at': now,
                'updated_at': now,
            }
            for row in rows
        ],
    )
    for row in rows:
        conn.execute(
            sheet_rows.update()
            .where(sheet_rows.c.id == row.id)
            .values(data=sa.func.json_set(sheet_rows.c.data, '$.approval_status', 'draft'))
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    sheets = sa.table(
        'sheets',
        sa.column('id', sa.Integer),
        sa.column('entity_type', sa.String),
        sa.column('columns', sa.JSON),
    )
    sheet_rows = sa.table(
        'sheet_rows',
        sa.column('id', sa.Integer),
        sa.column('sheet_id', sa.Integer),
        sa.column('data', sa.JSON),
    )

    sheet = conn.execute(
        sa.select(sheets.c.id, sheets.c.columns).where(
            sheets.c.entity_type == 'DataInventory'
        )
    ).first()
    if sheet is not None:
        conn.execute(
            sheets.update()
            .where(sheets.c.id == sheet.id)
            .values(
                columns=[
                    column
                    for column in (sheet.columns or [])
                    if column.get('key') != STATUS_COLUMN['key']
                ]
            )
        )
        conn.execute(
            sheet_rows.update()
            .where(sheet_rows.c.sheet_id == sheet.id)
            .values(data=sa.func.json_remove(sheet_rows.c.data, '$.approval_status'))
        )

    op.drop_index(op.f('ix_data_inventory_records_data_inventory_row_id'), table_name='data_inventory_records')
    op.drop_table('data_inventory_records')
