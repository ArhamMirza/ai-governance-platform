"""clean up ai system records orphaned by a sheet re-import

Revision ID: 4b7f2c9e0a13
Revises: 9c2c1b7fa804
Create Date: 2026-09-14 00:00:00.000000

"""
import os
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4b7f2c9e0a13'
down_revision: str | Sequence[str] | None = '9c2c1b7fa804'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    sheet_service.import_upload used to delete every row of a sheet and
    recreate all of them fresh on every re-upload. SQLite reuses a freed
    rowid, so a re-import did not reliably preserve which row was which AI
    system -- an AISystemLifecycle, RiskAssessment or ImpactAssessment
    (each unique on ai_system_row_id) could end up either pointing at
    nothing, or silently reattached to whatever unrelated system the next
    upload happened to create at that same id. import_upload now matches
    rows back to themselves instead of replacing them; this clears what a
    past re-import already left orphaned -- rows genuinely pointing at a
    sheet_rows id that no longer exists at all. (A silently-misattributed
    row, one now pointing at a live but wrong id, looks identical to a
    correctly-attached one and can't be told apart after the fact -- there
    is nothing further back to recover.)
    """
    conn = op.get_bind()

    for lifecycle_id, in conn.execute(
        sa.text(
            "SELECT id FROM ai_system_lifecycles "
            "WHERE ai_system_row_id NOT IN (SELECT id FROM sheet_rows)"
        )
    ).all():
        # Its own AISystem-entity evidence/folders were already swept by
        # 9c2c1b7fa804, using this identical predicate.
        conn.execute(
            sa.text("DELETE FROM ai_system_lifecycles WHERE id = :id"), {"id": lifecycle_id}
        )

    for assessment_id, in conn.execute(
        sa.text(
            "SELECT id FROM impact_assessments "
            "WHERE ai_system_row_id NOT IN (SELECT id FROM sheet_rows)"
        )
    ).all():
        conn.execute(
            sa.text(
                "DELETE FROM impact_factor_assessments WHERE impact_assessment_id = :id"
            ),
            {"id": assessment_id},
        )
        for evidence_id, storage_path in conn.execute(
            sa.text(
                "SELECT id, storage_path FROM evidence "
                "WHERE entity_type = 'ImpactAssessment' AND entity_id = :id"
            ),
            {"id": assessment_id},
        ).all():
            if storage_path:
                try:
                    os.remove(storage_path)
                except OSError:
                    pass
            conn.execute(
                sa.text(
                    "DELETE FROM framework_tags "
                    "WHERE entity_type = 'Evidence' AND entity_id = :id"
                ),
                {"id": evidence_id},
            )
            conn.execute(sa.text("DELETE FROM evidence WHERE id = :id"), {"id": evidence_id})
        conn.execute(
            sa.text(
                "DELETE FROM framework_tags "
                "WHERE entity_type = 'ImpactAssessment' AND entity_id = :id"
            ),
            {"id": assessment_id},
        )
        conn.execute(
            sa.text("DELETE FROM impact_assessments WHERE id = :id"), {"id": assessment_id}
        )

    for risk_assessment_id, sheet_id in conn.execute(
        sa.text(
            "SELECT id, sheet_id FROM risk_assessments "
            "WHERE ai_system_row_id NOT IN (SELECT id FROM sheet_rows)"
        )
    ).all():
        # Mirrors risk_assessment_service.delete_risk_assessment's own
        # cascade: every Risk Item row's evidence, then the sheet itself.
        for (row_id,) in conn.execute(
            sa.text("SELECT id FROM sheet_rows WHERE sheet_id = :sheet_id"),
            {"sheet_id": sheet_id},
        ).all():
            for evidence_id, storage_path in conn.execute(
                sa.text(
                    "SELECT id, storage_path FROM evidence "
                    "WHERE entity_type = 'RiskItem' AND entity_id = :id"
                ),
                {"id": row_id},
            ).all():
                if storage_path:
                    try:
                        os.remove(storage_path)
                    except OSError:
                        pass
                conn.execute(
                    sa.text(
                        "DELETE FROM framework_tags "
                        "WHERE entity_type = 'Evidence' AND entity_id = :id"
                    ),
                    {"id": evidence_id},
                )
                conn.execute(
                    sa.text("DELETE FROM evidence WHERE id = :id"), {"id": evidence_id}
                )
            conn.execute(
                sa.text(
                    "DELETE FROM folders WHERE entity_type = 'RiskItem' AND entity_id = :id"
                ),
                {"id": row_id},
            )
        conn.execute(
            sa.text("DELETE FROM sheet_rows WHERE sheet_id = :sheet_id"), {"sheet_id": sheet_id}
        )
        conn.execute(sa.text("DELETE FROM sheets WHERE id = :id"), {"id": sheet_id})
        conn.execute(
            sa.text(
                "DELETE FROM framework_tags "
                "WHERE entity_type = 'RiskAssessment' AND entity_id = :id"
            ),
            {"id": risk_assessment_id},
        )
        conn.execute(
            sa.text("DELETE FROM risk_assessments WHERE id = :id"), {"id": risk_assessment_id}
        )


def downgrade() -> None:
    """Downgrade schema.

    Nothing to restore -- these rows pointed at an AI system that no longer
    exists, and their files are deleted along with the rows, so what they
    held is already gone.
    """
