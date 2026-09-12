"""unique constraints for records meant to be single

Revision ID: 7a1f4c9d2e30
Revises: 033dd0c55736
Create Date: 2026-09-13 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7a1f4c9d2e30'
down_revision: str | Sequence[str] | None = '033dd0c55736'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Only these two sheets are meant to be the one sheet of their kind. A risk
# assessment gets a fresh sheet per assessment, all with the same entity_type,
# so this index has to be partial -- see app.models.sheet.
SINGLETON_SHEET_PREDICATE = "entity_type IN ('AISystemInventory', 'DataInventory')"
UNREVOKED_PREDICATE = "revoked_at IS NULL"


def _duplicates(conn, table: str, column: str, where: str | None = None) -> list[str]:
    clause = f" WHERE {where}" if where else ""
    rows = conn.execute(
        sa.text(
            f"SELECT {column} AS value, COUNT(*) AS n, GROUP_CONCAT(id) AS ids "
            f"FROM {table}{clause} GROUP BY {column} HAVING n > 1"
        )
    ).all()
    return [f"{column}={row.value} (ids {row.ids})" for row in rows]


def _refuse(table: str, duplicates: list[str], guidance: str) -> None:
    raise RuntimeError(
        f"Can't make {table} unique: it already holds duplicates -- "
        + "; ".join(duplicates)
        + f". {guidance} Then run this migration again."
    )


def upgrade() -> None:
    """Upgrade schema.

    Four records the app treats as one-of-a-kind had nothing in the database
    saying so, so two simultaneous requests could each create one: a second
    Data Inventory sheet, a second risk or impact assessment for the same AI
    system, a second standing CAIGO delegation. The services do check first,
    but every repository commits as it writes, so the check and the insert
    are separate transactions and neither request sees the other's.

    Each step refuses rather than guesses. Which of two risk assessments for
    one system to keep is a governance decision with approvals and evidence
    attached to it -- not something a migration should settle unattended.
    """
    conn = op.get_bind()

    duplicate_sheets = _duplicates(conn, 'sheets', 'entity_type', SINGLETON_SHEET_PREDICATE)
    if duplicate_sheets:
        _refuse(
            'sheets',
            duplicate_sheets,
            "Move any rows off the sheet you don't want and delete it.",
        )

    for table in ('risk_assessments', 'impact_assessments'):
        duplicates = _duplicates(conn, table, 'ai_system_row_id')
        if duplicates:
            _refuse(
                table,
                duplicates,
                "Decide which assessment for that AI system is the real one "
                "and delete the other through the app, so its sheet, evidence "
                "and framework tags go with it.",
            )

    # An expired delegation that was never revoked is spent -- its window has
    # closed, so it already grants nothing. Revoking it is bookkeeping, not a
    # governance decision, and without it the row would sit there forever
    # counting as the role's one standing delegation.
    conn.execute(
        sa.text(
            "UPDATE governance_role_delegations "
            "SET revoked_at = ends_at "
            "WHERE revoked_at IS NULL AND ends_at <= CURRENT_TIMESTAMP"
        )
    )
    duplicate_delegations = _duplicates(
        conn, 'governance_role_delegations', 'governance_role_id', UNREVOKED_PREDICATE
    )
    if duplicate_delegations:
        _refuse(
            'governance_role_delegations',
            duplicate_delegations,
            "Two people are standing in for the same role right now. Revoke "
            "the delegation that shouldn't be there.",
        )

    # Replacing the plain index rather than adding a second one: the models
    # declare these columns unique, so a database built by create_all has one
    # unique index under this name and a migrated one should match.
    for table in ('risk_assessments', 'impact_assessments'):
        op.drop_index(op.f(f'ix_{table}_ai_system_row_id'), table_name=table)
        op.create_index(
            op.f(f'ix_{table}_ai_system_row_id'), table, ['ai_system_row_id'], unique=True
        )

    op.create_index(
        'uq_sheets_singleton_entity_type',
        'sheets',
        ['entity_type'],
        unique=True,
        sqlite_where=sa.text(SINGLETON_SHEET_PREDICATE),
        postgresql_where=sa.text(SINGLETON_SHEET_PREDICATE),
    )
    op.create_index(
        'uq_one_standing_delegation_per_role',
        'governance_role_delegations',
        ['governance_role_id'],
        unique=True,
        sqlite_where=sa.text(UNREVOKED_PREDICATE),
        postgresql_where=sa.text(UNREVOKED_PREDICATE),
    )


def downgrade() -> None:
    """Downgrade schema.

    The expired delegations revoked on the way up stay revoked: they had
    already lapsed, so un-revoking them would not give anyone back an
    approval they could have used.
    """
    op.drop_index('uq_one_standing_delegation_per_role', table_name='governance_role_delegations')
    op.drop_index('uq_sheets_singleton_entity_type', table_name='sheets')
    for table in ('risk_assessments', 'impact_assessments'):
        op.drop_index(op.f(f'ix_{table}_ai_system_row_id'), table_name=table)
        op.create_index(
            op.f(f'ix_{table}_ai_system_row_id'), table, ['ai_system_row_id'], unique=False
        )
