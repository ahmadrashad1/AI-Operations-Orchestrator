"""Initial migration: create workflows, audit_logs, users tables.

Revision ID: 001_initial
Revises:
Create Date: 2026-05-12 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create workflows table
    op.create_table(
        "workflows",
        sa.Column("workflow_id", sa.String(50), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("current_state", sa.String(100), nullable=False),
        sa.Column("extraction", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("policy_results", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("approvals", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("execution_log", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("workflow_id"),
    )
    op.create_index("ix_workflows_tenant_id", "workflows", ["tenant_id"], unique=False)
    op.create_index("ix_workflows_status", "workflows", ["status"], unique=False)
    op.create_index("ix_workflows_created_at", "workflows", ["created_at"], unique=False)
    op.create_index("idx_tenant_created", "workflows", ["tenant_id", "created_at"], unique=False)
    op.create_index("idx_tenant_status", "workflows", ["tenant_id", "status"], unique=False)

    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(50), nullable=False),
        sa.Column("workflow_id", sa.String(50), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_workflow_id", "audit_logs", ["workflow_id"], unique=False)
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index(
        "idx_workflow_created", "audit_logs", ["workflow_id", "created_at"], unique=False
    )
    op.create_index(
        "idx_tenant_created_audit", "audit_logs", ["tenant_id", "created_at"], unique=False
    )

    # Create users table
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("roles", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)
    op.create_index("ix_users_is_active", "users", ["is_active"], unique=False)
    op.create_index("idx_tenant_email", "users", ["tenant_id", "email"], unique=False)

    # Create token_blacklist table
    op.create_table(
        "token_blacklist",
        sa.Column("jti", sa.String(500), nullable=False),
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column("blacklisted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index("ix_token_blacklist_user_id", "token_blacklist", ["user_id"], unique=False)
    op.create_index("idx_expires_at", "token_blacklist", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_expires_at", table_name="token_blacklist")
    op.drop_index("ix_token_blacklist_user_id", table_name="token_blacklist")
    op.drop_table("token_blacklist")

    op.drop_index("idx_tenant_email", table_name="users")
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.drop_index("idx_tenant_created_audit", table_name="audit_logs")
    op.drop_index("idx_workflow_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_workflow_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("idx_tenant_status", table_name="workflows")
    op.drop_index("idx_tenant_created", table_name="workflows")
    op.drop_index("ix_workflows_created_at", table_name="workflows")
    op.drop_index("ix_workflows_status", table_name="workflows")
    op.drop_index("ix_workflows_tenant_id", table_name="workflows")
    op.drop_table("workflows")
