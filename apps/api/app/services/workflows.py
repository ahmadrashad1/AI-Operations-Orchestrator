from __future__ import annotations

from fastapi import HTTPException, status

from app.core.security import Principal
from app.db.repositories import WorkflowRepository
from app.domain.models import WorkflowState
from app.domain.schemas import InternalAgentExecuteRequest, WorkflowCreateRequest
from app.orchestration.runtime import WorkflowRuntime
from app.services.audit import AuditService


class WorkflowService:
    def __init__(
        self,
        repository: WorkflowRepository,
        audit_service: AuditService,
        runtime: WorkflowRuntime,
    ) -> None:
        self.repository = repository
        self.audit_service = audit_service
        self.runtime = runtime

    def create_workflow(self, payload: WorkflowCreateRequest, principal: Principal) -> WorkflowState:
        tenant_id = principal.tenant_id
        if payload.tenant_id and payload.tenant_id != principal.tenant_id:
            if "Admin" not in principal.roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Workflow creation cannot target a different tenant.",
                )
            tenant_id = payload.tenant_id

        workflow = WorkflowState(
            tenant_id=tenant_id,
            submitted_by=principal.user_id,
            workflow_type=payload.workflow_type,
            request_text=payload.request_text,
            request_data=payload.request_data,
        )
        self.repository.create(workflow)
        self.audit_service.log(
            workflow_id=workflow.workflow_id,
            actor=principal.user_id,
            action="workflow.created",
            metadata={"workflow_type": workflow.workflow_type},
            tenant_id=workflow.tenant_id,
        )
        workflow = self.runtime.bootstrap(workflow=workflow)
        return self.repository.update(workflow)

    def get_workflow(self, workflow_id: str, principal: Principal) -> WorkflowState:
        workflow = self.repository.get(workflow_id)
        self._assert_tenant_access(workflow=workflow, principal=principal)
        return workflow

    def execute_agent(self, payload: InternalAgentExecuteRequest, principal: Principal) -> WorkflowState:
        workflow = self.repository.get(payload.workflow_id)
        self._assert_tenant_access(workflow=workflow, principal=principal)
        workflow = self.runtime.execute_agent(workflow=workflow, agent_name=payload.agent_name, actor=principal.user_id)
        return self.repository.update(workflow)

    def _assert_tenant_access(self, workflow: WorkflowState, principal: Principal) -> None:
        if workflow.tenant_id != principal.tenant_id and "Admin" not in principal.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The requested workflow belongs to a different tenant.",
            )
