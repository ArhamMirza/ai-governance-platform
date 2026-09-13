"""clean up documents orphaned by deletion

Revision ID: 9c2c1b7fa804
Revises: 7a1f4c9d2e30
Create Date: 2026-09-13 00:00:00.000000

"""
import os
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9c2c1b7fa804'
down_revision: str | Sequence[str] | None = '7a1f4c9d2e30'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# entity_type -> the table whose id space entity_id is drawn from, for every
# entity type reachable through the document browser in the UI (folders and
# evidence uploads). AISystem and RiskItem both point at sheet_rows -- one AI
# system inventory rows, the other risk-item rows -- so a row missing from
# that one table means the document's parent is gone either way.
DOCUMENT_ENTITY_TABLES = {
    "Policy": "policies",
    "Procedure": "procedures",
    "ImpactAssessment": "impact_assessments",
    "AISystem": "sheet_rows",
    "RiskItem": "sheet_rows",
}


def upgrade() -> None:
    """Upgrade schema.

    evidence_service.delete_all_for_entity used to miss any evidence filed in
    a subfolder (it only looked at the top level), and policy_service,
    procedure_service and ai_system_inventory_service never called it at
    all -- so deleting a draft policy or procedure, or an AI system past its
    retention period, left every document it held (and the file on disk)
    behind forever, along with any folder it was filed under. This clears
    what is already orphaned; the services now clean up as they go.
    """
    conn = op.get_bind()
    evidence = sa.table(
        'evidence',
        sa.column('id', sa.Integer),
        sa.column('entity_type', sa.String),
        sa.column('entity_id', sa.Integer),
        sa.column('storage_path', sa.String),
    )
    folders = sa.table(
        'folders',
        sa.column('id', sa.Integer),
        sa.column('entity_type', sa.String),
        sa.column('entity_id', sa.Integer),
    )
    framework_tags = sa.table(
        'framework_tags',
        sa.column('entity_type', sa.String),
        sa.column('entity_id', sa.Integer),
    )

    for entity_type, table_name in DOCUMENT_ENTITY_TABLES.items():
        parent_ids = sa.select(sa.column("id")).select_from(sa.table(table_name))

        rows = conn.execute(
            sa.select(evidence.c.id, evidence.c.storage_path).where(
                evidence.c.entity_type == entity_type,
                evidence.c.entity_id.not_in(parent_ids),
            )
        ).all()
        for evidence_id, storage_path in rows:
            if storage_path:
                try:
                    os.remove(storage_path)
                except OSError:
                    # Already gone, or the path doesn't resolve from wherever
                    # this migration runs -- the row is still cleared either
                    # way, which is the part a database migration can promise.
                    pass
            conn.execute(
                framework_tags.delete().where(
                    framework_tags.c.entity_type == "Evidence",
                    framework_tags.c.entity_id == evidence_id,
                )
            )
            conn.execute(evidence.delete().where(evidence.c.id == evidence_id))

        conn.execute(
            folders.delete().where(
                folders.c.entity_type == entity_type,
                folders.c.entity_id.not_in(parent_ids),
            )
        )


def downgrade() -> None:
    """Downgrade schema.

    Nothing to restore -- these documents and folders pointed at records
    that no longer exist, and the files themselves are deleted along with
    the rows, so what they held is already gone.
    """
