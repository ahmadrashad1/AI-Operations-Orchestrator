"""PostgreSQL repository implementations using SQLAlchemy."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLogRecordModel, TenantModel, UserModel, WorkflowStateModel
from app.db.repositories import (
    BaseAuditRepository,
    BaseTenantRepository,
    BaseUserRepository,
    BaseWorkflowRepository,
)
from app.domain.models import AuditLogRecord, WorkflowState

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


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
                user_id=workflow.user_id,
                request_text=workflow.request_text,
                status=workflow.status.value,
                current_state=workflow.current_state,
                extraction=(
                    workflow.extraction.model_dump() if workflow.extraction else None
                ),
                policy_results=(
                    workflow.policy_results.model_dump() if workflow.policy_results else None
                ),
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
            stmt = select(WorkflowStateModel).where(
                WorkflowStateModel.workflow_id == workflow_id
            )
            db_workflow = session.scalar(stmt)

            if db_workflow is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow '{workflow_id}' was not found.",
                )

            # Convert ORM model back to domain model
            return self._orm_to_domain(db_workflow)

    def list_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
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
            user_id=db_workflow.user_id,
            request_text=db_workflow.request_text,
            status=WorkflowStatus(db_workflow.status),
            current_state=db_workflow.current_state,
            extraction=(
                ExtractedRequest(**db_workflow.extraction)
                if db_workflow.extraction
                else None
            ),
            policy_results=(
                PolicyEvaluation(**db_workflow.policy_results)
                if db_workflow.policy_results
                else None
            ),
            approvals=(
                [ApprovalRecord(**a) for a in db_workflow.approvals]
                if db_workflow.approvals
                else []
            ),
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
                id=record.id or str(uuid.uuid4()),
                workflow_id=record.workflow_id,
                tenant_id=record.tenant_id,
                actor=record.actor,
                action=record.action,
                metadata_=record.metadata,
                created_at=record.created_at,
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

    def list_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100) -> list[AuditLogRecord]:
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
            id=db_record.id,
            workflow_id=db_record.workflow_id,
            tenant_id=db_record.tenant_id,
            actor=db_record.actor,
            action=db_record.action,
            metadata=db_record.metadata_ or {},
            created_at=db_record.created_at,
        )



class PostgresUserRepository(BaseUserRepository):
    """PostgreSQL implementation of user repository."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create_user(self, user: dict) -> dict:
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            db_user = UserModel(
                user_id=user.get("user_id") or str(uuid.uuid4()),
                tenant_id=user.get("tenant_id") or "",
                email=user.get("email"),
                hashed_password=user.get("hashed_password"),
                roles=user.get("roles") or [],
                is_active=user.get("is_active", True),
                created_at=user.get("created_at") or datetime.now(UTC),
                updated_at=user.get("created_at") or datetime.now(UTC),
            )
            session.add(db_user)
            session.commit()
            session.refresh(db_user)
            return db_user.to_dict()

    def get_user(self, user_id: str) -> dict | None:
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            db_user = session.scalar(stmt)
            return db_user.to_dict() if db_user else None

    def list_users(self, tenant_id: str | None = None) -> list[dict]:
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            if tenant_id:
                stmt = select(UserModel).where(UserModel.tenant_id == tenant_id).order_by(
                    UserModel.created_at.desc()
                )
            else:
                stmt = select(UserModel).order_by(UserModel.created_at.desc())
            users = session.scalars(stmt).all()
            return [u.to_dict() for u in users]

    def update_user(self, user_id: str, updates: dict) -> dict:
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            db_user = session.scalar(stmt)
            if db_user is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            for k, v in updates.items():
                if hasattr(db_user, k):
                    setattr(db_user, k, v)
            db_user.updated_at = datetime.now(UTC)
            session.commit()
            session.refresh(db_user)
            return db_user.to_dict()

    def delete_user(self, user_id: str) -> None:
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            stmt = select(UserModel).where(UserModel.user_id == user_id)
            db_user = session.scalar(stmt)
            if db_user is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            session.delete(db_user)
            session.commit()


class PostgresTenantRepository(BaseTenantRepository):
    """PostgreSQL implementation of tenant repository."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create_tenant(self, tenant: dict) -> dict:
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            db_t = TenantModel(
                tenant_id=tenant.get("tenant_id"),
                name=tenant.get("name"),
                created_at=tenant.get("created_at") or datetime.now(UTC),
                updated_at=tenant.get("updated_at") or datetime.now(UTC),
            )
            session.add(db_t)
            session.commit()
            session.refresh(db_t)
            return db_t.to_dict()

    def list_tenants(self) -> list[dict]:
        from sqlalchemy.orm import Session

        with Session(self.engine) as session:
            stmt = select(TenantModel).order_by(TenantModel.created_at.desc())
            tenants = session.scalars(stmt).all()
            return [t.to_dict() for t in tenants]
