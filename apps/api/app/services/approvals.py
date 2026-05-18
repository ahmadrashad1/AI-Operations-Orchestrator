from __future__ import annotations

from contextlib import nullcontext

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.locks import workflow_lock
from app.core.security import Principal
from app.db.repositories import WorkflowRepository
from app.domain.models import WorkflowState
from app.domain.schemas import ApprovalDecisionRequest
from app.orchestration.runtime import WorkflowRuntime
from app.services.audit import AuditService


class ApprovalService:
    def __init__(
        self,
        repository: WorkflowRepository,
        audit_service: AuditService,
        runtime: WorkflowRuntime,
    ) -> None:
        self.repository = repository
        self.audit_service = audit_service
        self.runtime = runtime

    def respond(self, payload: ApprovalDecisionRequest, principal: Principal) -> WorkflowState:
        settings = get_settings()
        lock_cm = (
            nullcontext(True)
            if settings.environment == "development"
            else workflow_lock(settings.redis_url, payload.workflow_id, timeout=15)
        )

        with lock_cm as acquired:
            if not acquired:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Workflow is temporarily locked; retry shortly.",
                )

            workflow = self.repository.get(payload.workflow_id)
            self._assert_tenant_access(workflow=workflow, principal=principal)
            workflow = self.runtime.process_approval_response(
                workflow=workflow,
                approval_id=payload.approval_id,
                decision=payload.decision,
                actor=principal.user_id,
                comment=payload.comment,
            )
            return self.repository.update(workflow)

    def _assert_tenant_access(self, workflow: WorkflowState, principal: Principal) -> None:
        if workflow.tenant_id != principal.tenant_id and "Admin" not in principal.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The requested workflow belongs to a different tenant.",
            )

