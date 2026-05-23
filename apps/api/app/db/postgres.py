"""PostgreSQL repository implementations using SQLAlchemy."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AuditLogRecordModel,
    UserModel,
    WorkflowStateModel,
    TokenBlacklistModel,
    PermissionModel,
)
from app.db.repositories import BaseAuditRepository, BaseWorkflowRepository
from app.db.repositories import BaseTokenBlacklistRepository
from app.domain.models import AuditLogRecord, WorkflowState

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


class PostgresUserRepository:
    """Lookup users stored in PostgreSQL (login / RBAC source of truth)."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_by_email(self, email: str) -> UserModel | None:
        normalized = email.strip().lower()
        with Session(self.engine) as session:
            stmt = select(UserModel).where(func.lower(UserModel.email) == normalized)
            return session.scalar(stmt)


class PostgresWorkflowRepository(BaseWorkflowRepository):
    """PostgreSQL implementation of workflow repository."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(self, workflow: WorkflowState) -> WorkflowState:
        with Session(self.engine) as session:
            # Convert domain model to ORM model
            db_workflow = WorkflowStateModel(
                workflow_id=workflow.workflow_id,
                tenant_id=workflow.tenant_id,
                user_id=workflow.submitted_by,
                request_text=workflow.request_text,
                status=workflow.status.value,
                current_state=workflow.current_state,
                extraction=workflow.extraction.model_dump() if workflow.extraction else None,
                policy_results=workflow.policy_results.model_dump()
                if workflow.policy_results
                else None,
                approvals=[approval.model_dump() for approval in workflow.approvals],
                execution_log=workflow.execution_log,
                created_at=workflow.created_at,
                updated_at=workflow.updated_at,
            )
            session.add(db_workflow)
            session.commit()
            session.refresh(db_workflow)
            return workflow

    def update(self, workflow: WorkflowState) -> WorkflowState:
        with Session(self.engine) as session:
            # Fetch existing workflow
            stmt = select(WorkflowStateModel).where(
                WorkflowStateModel.workflow_id == workflow.workflow_id
            )
            db_workflow = session.scalar(stmt)

            if db_workflow is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow '{workflow.workflow_id}' was not found.",
                )

            # Update fields
            db_workflow.status = workflow.status.value
            db_workflow.current_state = workflow.current_state
            db_workflow.extraction = (
                workflow.extraction.model_dump() if workflow.extraction else None
            )
            db_workflow.policy_results = (
                workflow.policy_results.model_dump() if workflow.policy_results else None
            )
            db_workflow.approvals = [approval.model_dump() for approval in workflow.approvals]
            db_workflow.execution_log = workflow.execution_log
            db_workflow.updated_at = datetime.now(UTC)

            session.commit()
            session.refresh(db_workflow)
            return workflow

    def get(self, workflow_id: str) -> WorkflowState:
        with Session(self.engine) as session:
            stmt = select(WorkflowStateModel).where(WorkflowStateModel.workflow_id == workflow_id)
            db_workflow = session.scalar(stmt)

            if db_workflow is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow '{workflow_id}' was not found.",
                )

            # Convert ORM model back to domain model
            return self._orm_to_domain(db_workflow)

    def list_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[WorkflowState]:
        with Session(self.engine) as session:
            stmt = (
                select(WorkflowStateModel)
                .where(WorkflowStateModel.tenant_id == tenant_id)
                .order_by(WorkflowStateModel.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            db_workflows = session.scalars(stmt).all()
            return [self._orm_to_domain(w) for w in db_workflows]

    def clear(self) -> None:
        """Clear all workflows (for testing only)."""
        with Session(self.engine) as session:
            session.query(WorkflowStateModel).delete()
            session.commit()

    @staticmethod
    def _orm_to_domain(db_workflow: WorkflowStateModel) -> WorkflowState:
        """Convert ORM model to domain model."""
        from app.domain.models import (
            ApprovalRecord,
            ExtractedRequest,
            PolicyEvaluation,
            WorkflowStatus,
        )

        return WorkflowState(
            workflow_id=db_workflow.workflow_id,
            tenant_id=db_workflow.tenant_id,
            submitted_by=db_workflow.user_id,
            request_text=db_workflow.request_text,
            status=WorkflowStatus(db_workflow.status),
            current_state=db_workflow.current_state,
            extraction=ExtractedRequest(**db_workflow.extraction)
            if db_workflow.extraction
            else None,
            policy_results=PolicyEvaluation(**db_workflow.policy_results)
            if db_workflow.policy_results
            else None,
            approvals=[ApprovalRecord(**a) for a in db_workflow.approvals]
            if db_workflow.approvals
            else [],
            execution_log=db_workflow.execution_log or [],
            created_at=db_workflow.created_at,
            updated_at=db_workflow.updated_at,
        )


class PostgresAuditRepository(BaseAuditRepository):
    """PostgreSQL implementation of audit repository."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def append(self, record: AuditLogRecord) -> AuditLogRecord:
        with Session(self.engine) as session:
            db_record = AuditLogRecordModel(
                id=record.log_id,
                workflow_id=record.workflow_id,
                tenant_id=record.tenant_id,
                actor=record.actor,
                action=record.action,
                event_metadata=record.metadata,
                created_at=record.timestamp,
            )
            session.add(db_record)
            session.commit()
            session.refresh(db_record)
            return self._orm_to_domain(db_record)

    def list_by_workflow(self, workflow_id: str) -> list[AuditLogRecord]:
        with Session(self.engine) as session:
            stmt = (
                select(AuditLogRecordModel)
                .where(AuditLogRecordModel.workflow_id == workflow_id)
                .order_by(AuditLogRecordModel.created_at.asc())
            )
            db_records = session.scalars(stmt).all()
            return [self._orm_to_domain(r) for r in db_records]

    def list_by_tenant(
        self, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> list[AuditLogRecord]:
        with Session(self.engine) as session:
            stmt = (
                select(AuditLogRecordModel)
                .where(AuditLogRecordModel.tenant_id == tenant_id)
                .order_by(AuditLogRecordModel.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            db_records = session.scalars(stmt).all()
            return [self._orm_to_domain(r) for r in db_records]

    def clear(self) -> None:
        """Clear all records (for testing only)."""
        with Session(self.engine) as session:
            session.query(AuditLogRecordModel).delete()
            session.commit()

    @staticmethod
    def _orm_to_domain(db_record: AuditLogRecordModel) -> AuditLogRecord:
        """Convert ORM model to domain model."""
        return AuditLogRecord(
            log_id=db_record.id,
            tenant_id=db_record.tenant_id,
            workflow_id=db_record.workflow_id,
            actor=db_record.actor,
            action=db_record.action,
            metadata=db_record.event_metadata or {},
            timestamp=db_record.created_at,
        )


class PostgresTokenBlacklistRepository(BaseTokenBlacklistRepository):
    """PostgreSQL-backed token blacklist repository."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def add(self, jti: str, user_id: str, expires_at) -> None:
        with Session(self.engine) as session:
            db_entry = TokenBlacklistModel(jti=jti, user_id=user_id, blacklisted_at=datetime.now(UTC), expires_at=expires_at)
            session.add(db_entry)
            session.commit()

    def is_blacklisted(self, jti: str) -> bool:
        with Session(self.engine) as session:
            stmt = select(TokenBlacklistModel).where(TokenBlacklistModel.jti == jti)
            db_entry = session.scalar(stmt)
            if db_entry is None:
                return False
            # Check expiry
            if db_entry.expires_at and db_entry.expires_at < datetime.now(UTC):
                # expired -- remove it
                session.delete(db_entry)
                session.commit()
                return False
            return True

    def clear(self) -> None:
        with Session(self.engine) as session:
            session.query(TokenBlacklistModel).delete()
            session.commit()

class PostgresPermissionRepository:
    """Postgres-backed permission repository."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_permissions(self) -> dict[str, list[str]]:
        from sqlalchemy import select

        with Session(self.engine) as session:
            stmt = select(PermissionModel)
            rows = session.scalars(stmt).all()
            return {r.permission: r.roles or [] for r in rows}

    def upsert_permission(self, permission: str, roles: list[str], description: str | None = None) -> None:
        from sqlalchemy import select

        with Session(self.engine) as session:
            stmt = select(PermissionModel).where(PermissionModel.permission == permission)
            row = session.scalar(stmt)
            if row is None:
                row = PermissionModel(permission=permission, roles=roles, description=description)
                session.add(row)
            else:
                row.roles = roles
                row.description = description
            session.commit()

    def clear(self) -> None:
        with Session(self.engine) as session:
            session.query(PermissionModel).delete()
            session.commit()
