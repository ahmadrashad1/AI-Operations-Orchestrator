from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_audit_service,
    get_metrics_collector,
    get_workflow_service,
    require_roles,
)
from app.core.security import Principal
from app.domain.schemas import EventPublishRequest, InternalAgentExecuteRequest, WorkflowEnvelope
from app.services.audit import AuditService
from app.observability.telemetry import MetricsCollector, TelemetrySnapshot
from app.services.workflows import WorkflowService

router = APIRouter()


@router.post("/agent/execute", response_model=WorkflowEnvelope)
def execute_agent(
    payload: InternalAgentExecuteRequest,
    principal: Principal = Depends(require_roles("Admin", "Manager")),
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowEnvelope:
    workflow = workflow_service.execute_agent(payload=payload, principal=principal)
    return WorkflowEnvelope(workflow=workflow)


@router.post("/event/publish")
def publish_event(
    payload: EventPublishRequest,
    principal: Principal = Depends(require_roles("Admin", "Manager", "Auditor")),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict[str, str]:
    audit_service.log(
        workflow_id=payload.workflow_id,
        actor=principal.user_id,
        action=payload.action,
        metadata=payload.metadata,
        tenant_id=principal.tenant_id,
    )
    return {"status": "accepted"}


@router.get("/metrics", response_model=TelemetrySnapshot)
def read_metrics(
    principal: Principal = Depends(require_roles("Admin", "Manager", "Auditor")),
    metrics_collector: MetricsCollector = Depends(get_metrics_collector),
) -> TelemetrySnapshot:
    _ = principal
    return metrics_collector.snapshot()
