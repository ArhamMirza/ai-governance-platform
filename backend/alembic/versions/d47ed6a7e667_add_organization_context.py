"""add organization context

Revision ID: d47ed6a7e667
Revises: 8020d85dc3ac
Create Date: 2026-09-20 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd47ed6a7e667'
down_revision: str | Sequence[str] | None = '8020d85dc3ac'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# See app.models.sheet -- widened to admit the two new organization-wide
# tables this record owns (internal/external issues, interested parties)
# alongside the two that were already singletons.
OLD_PREDICATE = "entity_type IN ('AISystemInventory', 'DataInventory')"
NEW_PREDICATE = (
    "entity_type IN ('AISystemInventory', 'DataInventory', "
    "'OrganizationalIssues', 'InterestedParties')"
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'organization_context',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_description', sa.Text(), nullable=True),
        sa.Column('ai_usage_overview', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('issues_sheet_id', sa.Integer(), nullable=False),
        sa.Column('interested_parties_sheet_id', sa.Integer(), nullable=False),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_review_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['issues_sheet_id'], ['sheets.id']),
        sa.ForeignKeyConstraint(['interested_parties_sheet_id'], ['sheets.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # Replacing the partial index rather than adding a second one -- see
    # migration 7a1f4c9d2e30, which created it with the narrower predicate.
    op.drop_index('uq_sheets_singleton_entity_type', table_name='sheets')
    op.create_index(
        'uq_sheets_singleton_entity_type',
        'sheets',
        ['entity_type'],
        unique=True,
        sqlite_where=sa.text(NEW_PREDICATE),
        postgresql_where=sa.text(NEW_PREDICATE),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_sheets_singleton_entity_type', table_name='sheets')
    op.create_index(
        'uq_sheets_singleton_entity_type',
        'sheets',
        ['entity_type'],
        unique=True,
        sqlite_where=sa.text(OLD_PREDICATE),
        postgresql_where=sa.text(OLD_PREDICATE),
    )
    op.drop_table('organization_context')
