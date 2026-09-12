"""add governance role delegations

Revision ID: 2ff8e382653f
Revises: 700269adb472
Create Date: 2026-09-12 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2ff8e382653f'
down_revision: str | Sequence[str] | None = '700269adb472'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('governance_role_delegations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('governance_role_id', sa.Integer(), nullable=False),
    sa.Column('delegate_user_id', sa.Integer(), nullable=False),
    sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['governance_role_id'], ['governance_roles.id'], ),
    sa.ForeignKeyConstraint(['delegate_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_governance_role_delegations_governance_role_id'), 'governance_role_delegations', ['governance_role_id'], unique=False)
    op.create_index(op.f('ix_governance_role_delegations_delegate_user_id'), 'governance_role_delegations', ['delegate_user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_governance_role_delegations_delegate_user_id'), table_name='governance_role_delegations')
    op.drop_index(op.f('ix_governance_role_delegations_governance_role_id'), table_name='governance_role_delegations')
    op.drop_table('governance_role_delegations')
