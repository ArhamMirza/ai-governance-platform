"""add two step sign in

Revision ID: b7e2d94a1c36
Revises: a41c9d07e3b2
Create Date: 2026-10-18 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e2d94a1c36"
down_revision: str | Sequence[str] | None = "a41c9d07e3b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_mfa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("secret_encrypted", sa.String(length=400), nullable=False),
        sa.Column("confirmed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("last_used_step", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_mfa_user_id"), "user_mfa", ["user_id"], unique=True)
    op.create_table(
        "mfa_recovery_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mfa_recovery_codes_user_id"), "mfa_recovery_codes", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_mfa_recovery_codes_code_hash"), "mfa_recovery_codes", ["code_hash"], unique=False
    )
    op.create_table(
        "security_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "require_mfa_for_admins", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("security_settings")
    op.drop_index(op.f("ix_mfa_recovery_codes_code_hash"), table_name="mfa_recovery_codes")
    op.drop_index(op.f("ix_mfa_recovery_codes_user_id"), table_name="mfa_recovery_codes")
    op.drop_table("mfa_recovery_codes")
    op.drop_index(op.f("ix_user_mfa_user_id"), table_name="user_mfa")
    op.drop_table("user_mfa")
