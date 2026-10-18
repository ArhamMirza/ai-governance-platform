"""add account security

Revision ID: a41c9d07e3b2
Revises: ff70e11bd4a0
Create Date: 2026-10-18 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a41c9d07e3b2"
down_revision: str | Sequence[str] | None = "ff70e11bd4a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column(
                "must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
        batch.add_column(
            sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True)
        )
    op.create_table(
        "password_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("password_hash", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_password_history_user_id"), "password_history", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_password_history_user_id"), table_name="password_history")
    op.drop_table("password_history")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("password_changed_at")
        batch.drop_column("must_change_password")
