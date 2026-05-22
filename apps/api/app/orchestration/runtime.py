from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.ai.extraction import RequestExtractionAgent
from app.ai.policy import PolicyEngine
from app.domain.models import ApprovalRecord, ApprovalStatus, WorkflowState, WorkflowStatus
from app.integrations.registry import ConnectorRegistry
from app.services.audit import AuditService
from app.orchestration.langgraph_adapter import run_workflow_graph

if TYPE_CHECKING:
    from app.services.queue import RedisJobQueue


class WorkflowRuntime:
    def __init__(
        self,
        extractor: RequestExtractionAgent,
        policy_engine: PolicyEngine,
        audit_service: AuditService,
        connector_registry: ConnectorRegistry,
        job_queue: RedisJobQueue | None = None,
    ) -> None:
        self.extractor = extractor
        self.policy_engine = policy_engine
        self.audit_service = audit_service
        self.connector_registry = connector_registry
        self.job_queue = job_queue

    def bootstrap(self, workflow: WorkflowState) -> WorkflowState:
        workflow = run_workflow_graph(self.extractor, self.policy_engine, self, workflow)
        workflow.updated_at = datetime.now(timezone.utc)
        return workflow

    def process_approval_response(
        self,
        workflow: WorkflowState,
        approval_id: str,
        decision: str,
        actor: str,
        comment: str | None,
    ) -> WorkflowState:
        target = next((approval for approval in workflow.approvals if approval.approval_id == approval_id), None)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval '{approval_id}' was not found.",
            )
        if target.status != ApprovalStatus.pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Approval '{approval_id}' has already been handled.",
            )

        target.status = ApprovalStatus.approved if decision == "approved" else ApprovalStatus.rejected
        target.responded_by = actor
        target.responded_at = datetime.now(timezone.utc)
        target.comment = comment

        self.audit_service.log(
            workflow_id=workflow.workflow_id,
            actor=actor,
            action=f"approval.{decision}",
            metadata={"approval_id": approval_id, "role": target.role, "comment": comment},
        )

        if target.status == ApprovalStatus.rejected:
            workflow.status = WorkflowStatus.rejected
            workflow.current_state = "rejected"
            workflow.execution_log.append({"event": "workflow.rejected", "approval_id": approval_id})
        elif all(approval.status == ApprovalStatus.approved for approval in workflow.approvals):
            workflow.status = WorkflowStatus.completed
            workflow.current_state = "completed"
            workflow.execution_log.append({"event": "workflow.completed", "mode": "approved"})
            self.audit_service.log(
                workflow_id=workflow.workflow_id,
                actor="orchestrator",
                action="workflow.completed",
                metadata={"mode": "approved"},
            )
        else:
            workflow.status = WorkflowStatus.waiting_approval
            workflow.current_state = "awaiting_additional_approvals"
            workflow.execution_log.append({"event": "approval.recorded", "approval_id": approval_id})

        workflow.updated_at = datetime.now(timezone.utc)
        return workflow

    def execute_agent(self, workflow: WorkflowState, agent_name: str, actor: str) -> WorkflowState:
        workflow.execution_log.append({"event": "agent.executed", "agent_name": agent_name, "actor": actor})
        self.audit_service.log(
            workflow_id=workflow.workflow_id,
            actor=actor,
            action="agent.executed",
            metadata={"agent_name": agent_name},
        )

        if agent_name == "policy-agent" and workflow.extraction is not None:
            workflow.policy_results = self.policy_engine.evaluate(workflow.extraction)
            workflow.current_state = "policy_re_evaluated"

        workflow.updated_at = datetime.now(timezone.utc)
        return workflow

    def _build_approvals(self, workflow: WorkflowState) -> list[ApprovalRecord]:
        approvals: list[ApprovalRecord] = []
        policy = workflow.policy_results
        if policy is None:
            return approvals

        if policy.needs_manager_approval:
            approvals.append(ApprovalRecord(role="Manager"))
        if policy.needs_finance_approval:
            approvals.append(ApprovalRecord(role="Finance"))
        if policy.requires_human_review:
            approvals.append(ApprovalRecord(role="Compliance"))
        return approvals

    def _dispatch_approval_request(self, workflow: WorkflowState, approval: ApprovalRecord) -> None:
        connector = self.connector_registry.get("slack")
        if connector is None or not connector.authenticate():
            self.audit_service.log(
                workflow_id=workflow.workflow_id,
                actor="connector-registry",
                action="approval.dispatch_skipped",
                metadata={"reason": "slack connector unavailable"},
            )
            return

        payload = {
            "workflow_id": workflow.workflow_id,
            "approval_id": approval.approval_id,
            "role": approval.role,
            "request_text": workflow.request_text,
            "estimated_cost": workflow.extraction.estimated_cost if workflow.extraction else None,
        }

        if not connector.validate(payload):
            self.audit_service.log(
                workflow_id=workflow.workflow_id,
                actor="slack",
                action="approval.dispatch_invalid",
                metadata=payload,
            )
            return

        # If job queue is available, enqueue dispatch; otherwise dispatch synchronously
        if self.job_queue:
            job = self.job_queue.enqueue(
                job_type="connector_dispatch",
                payload={
                    "connector": "slack",
                    "workflow_id": workflow.workflow_id,
                    "approval_id": approval.approval_id,
                    "dispatch_payload": payload,
                    "idempotency_key": f"{workflow.workflow_id}:{approval.approval_id}",
                },
            )
            self.audit_service.log(
                workflow_id=workflow.workflow_id,
                actor="job-queue",
                action="approval.dispatch_queued",
                metadata={"job_id": job.job_id},
            )
        else:
            # Fallback to synchronous dispatch
            dispatch = connector.execute(
                payload=payload,
                idempotency_key=f"{workflow.workflow_id}:{approval.approval_id}",
            )
            self.audit_service.log(
                workflow_id=workflow.workflow_id,
                actor="slack",
                action="approval.dispatched",
                metadata=dispatch.model_dump(),
            )
