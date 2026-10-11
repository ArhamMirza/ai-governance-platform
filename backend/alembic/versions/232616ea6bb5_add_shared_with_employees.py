"""add shared with employees

Revision ID: 232616ea6bb5
Revises: 11074b818da0
Create Date: 2026-10-11 18:52:51.344425

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "232616ea6bb5"
down_revision: str | Sequence[str] | None = "11074b818da0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # NOT NULL on tables that already have rows: everything existing starts
    # unshared, so nothing becomes visible to employees by upgrading.
    for table in ("policies", "procedures"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(
                sa.Column(
                    "shared_with_employees",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )


def downgrade() -> None:
    """Downgrade schema."""
    for table in ("procedures", "policies"):
        with op.batch_alter_table(table) as batch:
            batch.drop_column("shared_with_employees")
