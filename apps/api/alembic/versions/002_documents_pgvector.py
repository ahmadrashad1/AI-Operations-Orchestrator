"""Create pgvector documents table.

Revision ID: 002_documents_pgvector
Revises: 001_initial
Create Date: 2026-05-22 00:00:00.000000
"""
from __future__ import annotations

from alembic import op

revision = "002_documents_pgvector"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_documents_created_at ON documents (created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_documents_embedding")
    op.execute("DROP INDEX IF EXISTS ix_documents_created_at")
    op.execute("DROP TABLE IF EXISTS documents")
