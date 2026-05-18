"""SQLAlchemy ORM models for persistent storage."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Float, Index, String, Text, create_engine
from sqlalchemy.dialects.postgresql import JSON as PGJSON
from sqlalchemy.orm import declarative_base, Session

Base = declarative_base()


class WorkflowStateModel(Base):
    """SQLAlchemy ORM model for WorkflowState persistence."""

    __tablename__ = "workflows"

    workflow_id = Column(String(50), primary_key=True, nullable=False)
    tenant_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False)
    request_text = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, index=True)
    current_state = Column(String(100), nullable=False)
    extraction = Column(PGJSON, nullable=True)  # ExtractedRequest as JSON
    policy_results = Column(PGJSON, nullable=True)  # PolicyEvaluation as JSON
    approvals = Column(PGJSON, nullable=True)  # List[ApprovalRecord] as JSON
    execution_log = Column(PGJSON, nullable=True)  # List[Dict] as JSON
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_tenant_created", "tenant_id", "created_at"),
        Index("idx_tenant_status", "tenant_id", "status"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "request_text": self.request_text,
            "status": self.status,
            "current_state": self.current_state,
            "extraction": self.extraction,
            "policy_results": self.policy_results,
            "approvals": self.approvals,
            "execution_log": self.execution_log,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class AuditLogRecordModel(Base):
    """SQLAlchemy ORM model for AuditLogRecord persistence."""

    __tablename__ = "audit_logs"

    id = Column(String(50), primary_key=True, nullable=False)
    workflow_id = Column(String(50), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    actor = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    event_metadata = Column("metadata", PGJSON, nullable=True)  # Dict[str, Any] as JSON
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index("idx_workflow_created", "workflow_id", "created_at"),
        Index("idx_tenant_created", "tenant_id", "created_at"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "tenant_id": self.tenant_id,
            "actor": self.actor,
            "action": self.action,
            "metadata": self.event_metadata,
            "created_at": self.created_at,
        }


class UserModel(Base):
    """SQLAlchemy ORM model for User persistence."""

    __tablename__ = "users"

    user_id = Column(String(100), primary_key=True, nullable=False)
    tenant_id = Column(String(100), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=True)
    roles = Column(PGJSON, nullable=False, default=[])  # List[str]
    is_active = Column(String(50), nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("idx_tenant_email", "tenant_id", "email"),)

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "email": self.email,
            "roles": self.roles,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TokenBlacklistModel(Base):
    """SQLAlchemy ORM model for JWT token blacklist."""

    __tablename__ = "token_blacklist"

    jti = Column(String(500), primary_key=True, nullable=False)
    user_id = Column(String(100), nullable=False, index=True)
    blacklisted_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("idx_expires_at", "expires_at"),)

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "jti": self.jti,
            "user_id": self.user_id,
            "blacklisted_at": self.blacklisted_at,
            "expires_at": self.expires_at,
        }
