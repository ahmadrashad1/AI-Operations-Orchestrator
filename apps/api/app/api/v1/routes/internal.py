from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.api.dependencies import (
    get_audit_service,
    get_metrics_collector,
    get_reporting_service,
    get_workflow_service,
    require_roles,
)
from app.core.security import Principal
from app.domain.schemas import EventPublishRequest, InternalAgentExecuteRequest, WorkflowEnvelope
from app.domain.reporting import TenantReportingSummary
from app.services.audit import AuditService
from app.observability.telemetry import MetricsCollector, TelemetrySnapshot
from app.services.reporting import ReportingService
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


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
def read_metrics_prometheus(
    principal: Principal = Depends(require_roles("Admin", "Manager", "Auditor")),
    metrics_collector: MetricsCollector = Depends(get_metrics_collector),
) -> PlainTextResponse:
    """Return a Prometheus exposition of the internal telemetry snapshot.

    This is a lightweight adapter that converts the existing TelemetrySnapshot
    into the Prometheus text exposition format. It avoids adding new
    dependencies so the endpoint can be used as a quick-win for scraping.
    """
    _ = principal
    # Prefer serving the collector's prometheus registry if available
    try:
        data = metrics_collector.prometheus_metrics()
        if data:
            return PlainTextResponse(content=data, media_type="text/plain; version=0.0.4")
        # empty result falls through to snapshot fallback
    except Exception:
        # fall through to snapshot-based text
        pass
    snap = metrics_collector.snapshot()
    lines: list[str] = []
    lines.append('# HELP aiops_total_requests Total number of requests recorded')
    lines.append('# TYPE aiops_total_requests counter')
    lines.append(f'aiops_total_requests {snap.total_requests}')
    # Requests by method
    lines.append('# HELP aiops_requests_by_method Requests partitioned by HTTP method')
    lines.append('# TYPE aiops_requests_by_method gauge')
    for method, count in snap.requests_by_method.items():
        lines.append(f'aiops_requests_by_method{{method="{method}"}} {count}')

    # Requests by status
    lines.append('# HELP aiops_requests_by_status Requests partitioned by HTTP status code')
    lines.append('# TYPE aiops_requests_by_status gauge')
    for status, count in snap.requests_by_status.items():
        lines.append(f'aiops_requests_by_status{{status="{status}"}} {count}')

    # Requests by path (note: high-cardinality caution)
    lines.append('# HELP aiops_requests_by_path Requests partitioned by request path')
    lines.append('# TYPE aiops_requests_by_path gauge')
    for path, count in snap.requests_by_path.items():
        esc_path = path.replace('"', '\\"')
        lines.append(f'aiops_requests_by_path{{path="{esc_path}"}} {count}')
    lines.append('# HELP aiops_average_request_duration_ms Average request duration in ms')
    lines.append('# TYPE aiops_average_request_duration_ms gauge')
    lines.append(f'aiops_average_request_duration_ms {snap.average_duration_ms}')
    body = "\n".join(lines) + "\n"
    return PlainTextResponse(content=body, media_type="text/plain; version=0.0.4")


@router.get("/reports/tenant-summary", response_model=TenantReportingSummary)
def tenant_summary(
    tenant_id: str | None = None,
    principal: Principal = Depends(require_roles("Admin", "Manager", "Auditor")),
    reporting_service: ReportingService = Depends(get_reporting_service),
) -> TenantReportingSummary:
    return reporting_service.tenant_summary(principal=principal, tenant_id=tenant_id)
