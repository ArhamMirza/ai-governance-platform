"""add ai tool kind

Revision ID: e63c9a24b7d1
Revises: d52b8f13a6c9
Create Date: 2026-10-20 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e63c9a24b7d1"
down_revision: str | Sequence[str] | None = "d52b8f13a6c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema. Every tool and request that exists is a web one."""
    with op.batch_alter_table("ai_tools", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("kind", sa.String(length=20), server_default="web", nullable=False)
        )
    with op.batch_alter_table("ai_tool_requests", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("kind", sa.String(length=20), server_default="web", nullable=False)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("ai_tool_requests", schema=None) as batch_op:
        batch_op.drop_column("kind")
    with op.batch_alter_table("ai_tools", schema=None) as batch_op:
        batch_op.drop_column("kind")
