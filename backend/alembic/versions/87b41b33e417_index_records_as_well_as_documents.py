"""index records as well as documents

Generalises the chunk store so a passage can come from any record, not only
an uploaded file. A chunk gains two identities: what it *is* (source_type /
source_id) and what it is *about* (entity_type / entity_id), which is what a
search scoped to one AI system searches on.

Existing chunks are all evidence, so they backfill exactly: source becomes
the evidence row, entity becomes whatever that evidence was uploaded
against, and source_title becomes the filename.

Also adds index_queue, which records that a source's text has changed so the
reindex can happen off the write path.

Revision ID: 87b41b33e417
Revises: 120b9e7b54a4
Create Date: 2026-09-13 23:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "87b41b33e417"
down_revision: str | Sequence[str] | None = "120b9e7b54a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Added with defaults so the columns can be NOT NULL against existing
    # rows; the backfill immediately replaces the placeholder values.
    op.add_column(
        "document_chunks",
        sa.Column("source_type", sa.String(length=30), nullable=False, server_default="Evidence"),
    )
    op.add_column(
        "document_chunks",
        sa.Column("source_id", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "document_chunks",
        sa.Column("source_title", sa.String(length=300), nullable=False, server_default=""),
    )
    op.add_column(
        "document_chunks",
        sa.Column("entity_type", sa.String(length=30), nullable=False, server_default=""),
    )
    op.add_column(
        "document_chunks",
        sa.Column("entity_id", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("document_chunks", sa.Column("injection_findings", sa.JSON(), nullable=True))

    # Every existing chunk came from evidence, so each one can say exactly
    # what it is and what it is about.
    op.execute(
        """
        UPDATE document_chunks SET
            source_type = 'Evidence',
            source_id = evidence_id,
            source_title = COALESCE(
                (SELECT filename FROM evidence WHERE evidence.id = document_chunks.evidence_id), ''
            ),
            entity_type = COALESCE(
                (SELECT entity_type FROM evidence WHERE evidence.id = document_chunks.evidence_id),
                ''
            ),
            entity_id = COALESCE(
                (SELECT entity_id FROM evidence WHERE evidence.id = document_chunks.evidence_id), 0
            ),
            injection_findings = (
                SELECT injection_findings FROM evidence
                WHERE evidence.id = document_chunks.evidence_id
            )
        """
    )
    # A chunk whose evidence row has gone is unreachable and uncitable.
    op.execute("DELETE FROM document_chunks WHERE entity_type = ''")

    op.drop_index(op.f("ix_document_chunks_evidence_id"), table_name="document_chunks")
    # A table rebuild, not a plain DROP COLUMN: evidence_id carries a foreign
    # key, and SQLite refuses to drop a column that does.
    with op.batch_alter_table("document_chunks") as batch:
        batch.drop_column("evidence_id")

    op.create_index(
        "ix_document_chunks_source", "document_chunks", ["source_type", "source_id"], unique=False
    )
    op.create_index(
        "ix_document_chunks_entity", "document_chunks", ["entity_type", "entity_id"], unique=False
    )

    op.create_table(
        "index_queue",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_type", "source_id", name="uq_index_queue_source"),
    )

    # Records that existed before this migration have never been indexed, so
    # queue every one of them rather than leaving them silently unsearchable.
    for source_type, table in [
        ("Policy", "policies"),
        ("Procedure", "procedures"),
        ("ImpactAssessment", "impact_assessments"),
    ]:
        op.execute(
            f"INSERT INTO index_queue (source_type, source_id, queued_at) "  # noqa: S608
            f"SELECT '{source_type}', id, CURRENT_TIMESTAMP FROM {table}"
        )
    # Sheet rows carry their kind on the sheet, not the row.
    for source_type, sheet_entity in [
        ("AISystem", "AISystemInventory"),
        ("DataInventory", "DataInventory"),
        ("RiskItem", "RiskAssessment"),
    ]:
        op.execute(
            "INSERT INTO index_queue (source_type, source_id, queued_at) "  # noqa: S608
            f"SELECT '{source_type}', sheet_rows.id, CURRENT_TIMESTAMP FROM sheet_rows "
            "JOIN sheets ON sheets.id = sheet_rows.sheet_id "
            f"WHERE sheets.entity_type = '{sheet_entity}'"
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("index_queue")
    op.drop_index("ix_document_chunks_entity", table_name="document_chunks")
    op.drop_index("ix_document_chunks_source", table_name="document_chunks")

    # Only evidence chunks can be represented by the old shape.
    op.execute("DELETE FROM document_chunks WHERE source_type != 'Evidence'")
    op.add_column(
        "document_chunks",
        sa.Column("evidence_id", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute("UPDATE document_chunks SET evidence_id = source_id")
    op.create_index(
        op.f("ix_document_chunks_evidence_id"), "document_chunks", ["evidence_id"], unique=False
    )

    for column in (
        "injection_findings",
        "entity_id",
        "entity_type",
        "source_title",
        "source_id",
        "source_type",
    ):
        op.drop_column("document_chunks", column)
