"""drop framework tags for deleted evidence

Revision ID: 25510001cc32
Revises: bcedd33eeb8a
Create Date: 2026-09-12 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '25510001cc32'
down_revision: str | Sequence[str] | None = 'bcedd33eeb8a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Deleting a tagged document used to leave its framework tags behind, and
    the Statement of Applicability reads those tags as evidence that a control
    is covered -- so a deleted document kept counting towards compliance.
    evidence_service now clears them on delete; this clears the ones already
    orphaned.

    Only Evidence is affected: Policy, Procedure and both assessment types
    have always cleared their tags on delete.
    """
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM framework_tags
            WHERE entity_type = 'Evidence'
              AND entity_id NOT IN (SELECT id FROM evidence)
            """
        )
    )


def downgrade() -> None:
    """Downgrade schema.

    Nothing to restore -- these rows pointed at documents that no longer
    exist, so the information they carried is already gone.
    """
