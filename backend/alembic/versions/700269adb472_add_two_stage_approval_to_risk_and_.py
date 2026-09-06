"""add two stage approval to risk and impact assessments

Revision ID: 700269adb472
Revises: f767eee32b3d
Create Date: 2026-09-06 16:37:17.134808

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '700269adb472'
down_revision: str | Sequence[str] | None = 'f767eee32b3d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    for table in ('risk_assessments', 'impact_assessments'):
        op.add_column(table, sa.Column('owner_approved_by', sa.Integer(), nullable=True))
        op.add_column(
            table, sa.Column('owner_approved_at', sa.DateTime(timezone=True), nullable=True)
        )
        op.add_column(table, sa.Column('caigo_approved_by', sa.Integer(), nullable=True))
        op.add_column(
            table, sa.Column('caigo_approved_at', sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in ('risk_assessments', 'impact_assessments'):
        op.drop_column(table, 'caigo_approved_at')
        op.drop_column(table, 'caigo_approved_by')
        op.drop_column(table, 'owner_approved_at')
        op.drop_column(table, 'owner_approved_by')
