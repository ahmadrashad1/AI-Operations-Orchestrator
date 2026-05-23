"""Create permissions table.

Revision ID: 004_permissions
Revises: 003_tenants
Create Date: 2026-05-24 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "004_permissions"
down_revision = "003_tenants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("permission", sa.String(200), nullable=False),
        sa.Column("roles", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("permission"),
    )


def downgrade() -> None:
    op.drop_table("permissions")
