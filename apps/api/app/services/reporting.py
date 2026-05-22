from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.core.security import Principal
from app.db.repositories import AuditRepository, WorkflowRepository
from app.domain.models import WorkflowState
from app.domain.reporting import TenantReportingSummary


class ReportingService:
    def __init__(self, workflow_repository: WorkflowRepository, audit_repository: AuditRepository) -> None:
        self.workflow_repository = workflow_repository
        self.audit_repository = audit_repository

    def tenant_summary(self, *, principal: Principal, tenant_id: str | None = None) -> TenantReportingSummary:
        target_tenant = tenant_id or principal.tenant_id
        self._assert_tenant_access(principal=principal, tenant_id=target_tenant)

        workflows = self.workflow_repository.list_by_tenant(target_tenant, skip=0, limit=1000)
        audit_records = self.audit_repository.list_by_tenant(target_tenant, skip=0, limit=1000)

        status_counts = Counter(workflow.status.value for workflow in workflows)
        pending_approvals = sum(
            1
            for workflow in workflows
            if workflow.status.value in {"pending", "waiting_approval"}
            and any(approval.status.value == "pending" for approval in workflow.approvals)
        )

        recent_workflows = sorted(workflows, key=lambda workflow: workflow.updated_at, reverse=True)[:5]
        recent_actions = [record.action for record in sorted(audit_records, key=lambda record: record.timestamp, reverse=True)[:5]]

        return TenantReportingSummary(
            tenant_id=target_tenant,
            workflow_count=len(workflows),
            workflows_by_status=dict(status_counts),
            pending_approvals=pending_approvals,
            audit_event_count=len(audit_records),
            recent_workflow_ids=[workflow.workflow_id for workflow in recent_workflows],
            recent_actions=recent_actions,
            generated_at=datetime.now(UTC),
        )

    def _assert_tenant_access(self, *, principal: Principal, tenant_id: str) -> None:
        if tenant_id != principal.tenant_id and "Admin" not in principal.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Reporting is limited to the authenticated tenant.",
            )