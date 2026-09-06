"""add owner_id to ai_system_lifecycles

Revision ID: f767eee32b3d
Revises: 1c71a215bf83
Create Date: 2026-09-06 14:22:16.886014

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f767eee32b3d'
down_revision: str | Sequence[str] | None = '1c71a215bf83'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'ai_system_lifecycles',
        sa.Column('owner_id', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('ai_system_lifecycles', 'owner_id')
