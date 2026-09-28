"""add ai incidents

Revision ID: 90680b0920d0
Revises: 470af63753aa
Create Date: 2026-09-28 21:33:36.401661

Adds the ai_incidents table, and EU AI Act Article 73 (reporting of serious
incidents) to the framework reference data -- the obligation the incident
log's reporting deadlines track.

Article 73 is inserted only if it isn't already there: migration 7cfda4cd2ddb
reads the live EU_AI_ACT_CONTROLS list, so a database built from scratch
already gets it from that migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "90680b0920d0"
down_revision: str | Sequence[str] | None = "470af63753aa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen here rather than imported, so later edits to the reference data
# can't change what this migration did.
_ART_73_CODE = "Art.73"
_ART_73_TITLE = "Reporting of serious incidents"
_ART_73_DESCRIPTION = (
    "Providers of high-risk AI systems shall report any serious incident to the market "
    "surveillance authority within 15 days of becoming aware of it -- within 10 days of "
    "a death, and within 2 days of a widespread infringement or serious and "
    "irreversible disruption of critical infrastructure."
)


def _framework_controls_table() -> sa.Table:
    return sa.table(
        "framework_controls",
        sa.column("id", sa.Integer),
        sa.column("framework", sa.String),
        sa.column("code", sa.String),
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("category", sa.String),
    )


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ai_incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("ai_system_row_id", sa.Integer(), nullable=True),
        sa.Column("detected_on", sa.Date(), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("impact_description", sa.Text(), nullable=True),
        sa.Column("immediate_actions", sa.Text(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("is_serious", sa.Boolean(), nullable=False),
        sa.Column("serious_category", sa.String(length=40), nullable=True),
        sa.Column("authority_notified_on", sa.Date(), nullable=True),
        sa.Column("authority_reference", sa.String(length=200), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ai_system_row_id"],
            ["sheet_rows.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_incidents_ai_system_row_id"),
        "ai_incidents",
        ["ai_system_row_id"],
        unique=False,
    )

    conn = op.get_bind()
    controls = _framework_controls_table()
    existing = conn.execute(
        sa.select(controls.c.id)
        .where(controls.c.framework == "eu_ai_act")
        .where(controls.c.code == _ART_73_CODE)
    ).first()
    if existing is None:
        op.bulk_insert(
            controls,
            [
                {
                    "framework": "eu_ai_act",
                    "code": _ART_73_CODE,
                    "title": _ART_73_TITLE,
                    "description": _ART_73_DESCRIPTION,
                    "category": "clause",
                }
            ],
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    controls = _framework_controls_table()
    art_73 = conn.execute(
        sa.select(controls.c.id)
        .where(controls.c.framework == "eu_ai_act")
        .where(controls.c.code == _ART_73_CODE)
    ).first()
    if art_73 is not None:
        tags = sa.table("framework_tags", sa.column("framework_control_id", sa.Integer))
        conn.execute(sa.delete(tags).where(tags.c.framework_control_id == art_73.id))
        conn.execute(sa.delete(controls).where(controls.c.id == art_73.id))

    op.drop_index(op.f("ix_ai_incidents_ai_system_row_id"), table_name="ai_incidents")
    op.drop_table("ai_incidents")
