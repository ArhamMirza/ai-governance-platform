"""clear dangling dataset ai system links

Revision ID: 033dd0c55736
Revises: 25510001cc32
Create Date: 2026-09-13 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '033dd0c55736'
down_revision: str | Sequence[str] | None = '25510001cc32'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Deleting an AI system used to leave its datasets pointing at a sheet row
    that no longer existed -- the grid rendered those as "4 (unrecognized)" in
    the AI System picker. ai_system_inventory_service.delete_row now unlinks
    them; this clears the ones already dangling.

    The dataset rows themselves are untouched: only the broken link is
    removed, the same thing the service now does on delete.
    """
    conn = op.get_bind()
    sheets = sa.table(
        'sheets', sa.column('id', sa.Integer), sa.column('entity_type', sa.String)
    )
    sheet_rows = sa.table(
        'sheet_rows',
        sa.column('id', sa.Integer),
        sa.column('sheet_id', sa.Integer),
        sa.column('data', sa.JSON),
    )

    data_sheet_id = conn.execute(
        sa.select(sheets.c.id).where(sheets.c.entity_type == 'DataInventory')
    ).scalar()
    inventory_sheet_id = conn.execute(
        sa.select(sheets.c.id).where(sheets.c.entity_type == 'AISystemInventory')
    ).scalar()
    if data_sheet_id is None:
        return

    live_ids = {
        str(row_id)
        for row_id in conn.execute(
            sa.select(sheet_rows.c.id).where(sheet_rows.c.sheet_id == inventory_sheet_id)
        ).scalars()
    } if inventory_sheet_id is not None else set()

    datasets = conn.execute(
        sa.select(sheet_rows.c.id, sheet_rows.c.data).where(
            sheet_rows.c.sheet_id == data_sheet_id
        )
    ).all()
    for dataset in datasets:
        link = str((dataset.data or {}).get('ai_system_row_id') or '').strip()
        if not link or link in live_ids:
            continue
        conn.execute(
            sheet_rows.update()
            .where(sheet_rows.c.id == dataset.id)
            .values(data=sa.func.json_remove(sheet_rows.c.data, '$.ai_system_row_id'))
        )


def downgrade() -> None:
    """Downgrade schema.

    Nothing to restore -- these links pointed at AI systems that no longer
    exist, so what they referred to is already gone.
    """
