"""Create tenants table.

Revision ID: 003_tenants
Revises: 002_documents_pgvector
Create Date: 2026-05-22 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003_tenants"
down_revision = "002_documents_pgvector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id"),
    )
    op.create_index("ix_tenants_name", "tenants", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tenants_name", table_name="tenants")
    op.drop_table("tenants")
