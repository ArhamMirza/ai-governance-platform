"""add ai roles

Revision ID: b3a12532bf17
Revises: 819ebf063516
Create Date: 2026-10-07 19:39:22.068926

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3a12532bf17"
down_revision: str | Sequence[str] | None = "819ebf063516"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("ai_system_lifecycles", sa.Column("ai_roles", sa.JSON(), nullable=True))
    # NOT NULL on a table that may already have its row: existing contexts
    # start with no AI roles recorded.
    with op.batch_alter_table("organization_context") as batch:
        batch.add_column(
            sa.Column("ai_roles", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("organization_context") as batch:
        batch.drop_column("ai_roles")
    op.drop_column("ai_system_lifecycles", "ai_roles")
