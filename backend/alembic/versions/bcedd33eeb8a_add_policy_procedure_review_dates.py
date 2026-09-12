"""add policy and procedure review dates

Revision ID: bcedd33eeb8a
Revises: 1b5d8bf92739
Create Date: 2026-09-12 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bcedd33eeb8a'
down_revision: str | Sequence[str] | None = '1b5d8bf92739'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Deliberately no backfill. Neither table stores an approval date to derive
    a review date from, and inventing one would put every already-approved
    policy straight into the dashboard's overdue-review count the moment this
    deploys. Existing records stay null -- review_cadence.is_review_overdue
    treats that as "not due" -- and pick up a date at their next approval.
    """
    op.add_column('policies', sa.Column('next_review_date', sa.Date(), nullable=True))
    op.add_column('procedures', sa.Column('next_review_date', sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('procedures', 'next_review_date')
    op.drop_column('policies', 'next_review_date')
