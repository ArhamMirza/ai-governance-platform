"""track ai cache tokens

Revision ID: f85e1c46d9a3
Revises: e63c9a24b7d1
Create Date: 2026-10-23 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f85e1c46d9a3"
down_revision: str | Sequence[str] | None = "e63c9a24b7d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema. Calls already logged read as zero: they didn't say."""
    with op.batch_alter_table("ai_usage", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("cache_read_tokens", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.add_column(
            sa.Column("cache_write_tokens", sa.Integer(), server_default="0", nullable=False)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("ai_usage", schema=None) as batch_op:
        batch_op.drop_column("cache_write_tokens")
        batch_op.drop_column("cache_read_tokens")
