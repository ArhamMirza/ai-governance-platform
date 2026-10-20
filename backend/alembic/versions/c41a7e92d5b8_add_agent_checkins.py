"""add agent checkins

Revision ID: c41a7e92d5b8
Revises: b7e2d94a1c36
Create Date: 2026-10-20 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c41a7e92d5b8"
down_revision: str | Sequence[str] | None = "b7e2d94a1c36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ai_agent_checkins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_ref", sa.String(length=320), nullable=False),
        sa.Column("first_seen", sa.Date(), nullable=False),
        sa.Column("last_seen", sa.Date(), nullable=False),
        sa.Column("extension_version", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ai_agent_checkins", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ai_agent_checkins_last_seen"), ["last_seen"], unique=False)
        batch_op.create_index(batch_op.f("ix_ai_agent_checkins_user_ref"), ["user_ref"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("ai_agent_checkins", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ai_agent_checkins_user_ref"))
        batch_op.drop_index(batch_op.f("ix_ai_agent_checkins_last_seen"))
    op.drop_table("ai_agent_checkins")
