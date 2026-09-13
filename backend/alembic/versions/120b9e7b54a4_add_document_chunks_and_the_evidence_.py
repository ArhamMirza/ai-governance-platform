"""add document chunks and the evidence index

Creates the three tables document search runs on, all inside the SQLite file
the app already has:

- ``document_chunks``     the passages themselves, with their provenance
- ``document_chunks_fts`` an FTS5 mirror of the text, for BM25 keyword search
- ``chunk_vectors``       a sqlite-vec table of embeddings, for meaning

The vec0 table is only created where the sqlite-vec extension can be loaded.
Where it cannot, the migration still succeeds and search runs on keywords
alone -- a deployment should not fail to upgrade over an optional index.

Revision ID: 120b9e7b54a4
Revises: f310dbc52749
Create Date: 2026-09-13 22:04:58.039869

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.vector_store import EMBEDDING_DIMENSIONS

# revision identifiers, used by Alembic.
revision: str = '120b9e7b54a4'
down_revision: str | Sequence[str] | None = 'f310dbc52749'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('document_chunks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('evidence_id', sa.Integer(), nullable=False),
    sa.Column('ordinal', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('section', sa.String(length=200), nullable=True),
    sa.Column('source', sa.String(length=10), nullable=False),
    sa.Column('token_estimate', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_chunks_evidence_id'), 'document_chunks', ['evidence_id'], unique=False)
    # Existing evidence lands on "pending", which is what the backfill
    # command looks for -- documents uploaded before search existed are
    # waiting to be indexed, not silently considered done.
    op.add_column('evidence', sa.Column('index_status', sa.String(length=20), nullable=False, server_default='pending'))
    op.add_column('evidence', sa.Column('index_detail', sa.String(length=300), nullable=True))
    op.add_column('evidence', sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('evidence', sa.Column('injection_findings', sa.JSON(), nullable=True))
    op.create_index(op.f('ix_evidence_index_status'), 'evidence', ['index_status'], unique=False)

    connection = op.get_bind()
    # rowid is the chunk id, so a BM25 hit joins straight back to its row.
    connection.exec_driver_sql(
        "CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(text)"
    )
    try:
        connection.exec_driver_sql(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vectors USING vec0("
            f"chunk_id INTEGER PRIMARY KEY, embedding FLOAT[{EMBEDDING_DIMENSIONS}])"
        )
    except sa.exc.OperationalError:
        # No sqlite-vec on this machine. Keyword search still works, and the
        # table is created on first write if the extension appears later.
        pass


def downgrade() -> None:
    """Downgrade schema."""
    connection = op.get_bind()
    connection.exec_driver_sql("DROP TABLE IF EXISTS chunk_vectors")
    connection.exec_driver_sql("DROP TABLE IF EXISTS document_chunks_fts")
    op.drop_index(op.f('ix_evidence_index_status'), table_name='evidence')
    op.drop_column('evidence', 'injection_findings')
    op.drop_column('evidence', 'indexed_at')
    op.drop_column('evidence', 'index_detail')
    op.drop_column('evidence', 'index_status')
    op.drop_index(op.f('ix_document_chunks_evidence_id'), table_name='document_chunks')
    op.drop_table('document_chunks')
