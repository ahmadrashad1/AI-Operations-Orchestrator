from __future__ import annotations

from app.ai.extraction import RequestExtractionAgent
from app.ai.policy import PolicyEngine
from app.domain.models import WorkflowState
from app.orchestration.langgraph_adapter import run_workflow_graph
from app.orchestration.runtime import WorkflowRuntime
from app.services.audit import AuditService


class FlakyConnector:
    name = "slack"

    def __init__(self, failures_before_success: int) -> None:
        self.dispatched: list[dict[str, object]] = []
        self.failures_before_success = failures_before_success
        self.attempts = 0

    def authenticate(self) -> bool:
        return True

    def validate(self, payload) -> bool:
        return True

    def execute(self, payload, idempotency_key):
        self.attempts += 1
        if self.attempts <= self.failures_before_success:
            raise RuntimeError("temporary slack outage")

        self.dispatched.append({"payload": payload, "idempotency_key": idempotency_key})
        return type("Dispatch", (), {"model_dump": lambda self: {"status": "queued"}})()


class MockRegistry:
    def __init__(self, connector) -> None:
        self._connector = connector

    def get(self, name: str):
        if name == self._connector.name:
            return self._connector
        return None


class MemoryAuditRepository:
    def __init__(self) -> None:
        self.records = []

    def append(self, record):
        self.records.append(record)
        return record

    def list_by_workflow(self, workflow_id: str):
        return [record for record in self.records if record.workflow_id == workflow_id]

    def list_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100):
        records = [record for record in self.records if record.tenant_id == tenant_id]
        return records[skip : skip + limit]

    def clear(self):
        self.records.clear()


def _build_runtime(connector) -> WorkflowRuntime:
    extractor = RequestExtractionAgent()
    settings = type("S", (), {"manager_approval_threshold": 3000.0, "finance_approval_threshold": 5000.0})()
    policy = PolicyEngine(settings=settings)
    audit = AuditService(repository=MemoryAuditRepository())
    return WorkflowRuntime(
        extractor=extractor,
        policy_engine=policy,
        audit_service=audit,
        connector_registry=MockRegistry(connector),
        job_queue=None,
    )


def test_langgraph_adapter_retries_then_dispatches() -> None:
    connector = FlakyConnector(failures_before_success=1)
    runtime = _build_runtime(connector)
    extractor = runtime.extractor
    policy = runtime.policy_engine
    workflow = WorkflowState(tenant_id="tenant-a", submitted_by="user-1", request_text="Need 9 monitors for engineering")

    result = run_workflow_graph(extractor, policy, runtime, workflow)

    assert result.status == result.status.__class__.waiting_approval
    assert result.current_state == "dispatch_completed"
    assert [approval.role for approval in result.approvals] == ["Manager"]
    assert connector.attempts == 2
    assert len(connector.dispatched) == 1
    assert any(entry["event"] == "request.extracted" for entry in result.execution_log)
    assert any(entry["event"] == "policy.evaluated" for entry in result.execution_log)
    assert any(entry["event"] == "approval.dispatch_retry_scheduled" for entry in result.execution_log)


def test_langgraph_adapter_terminal_error_branch() -> None:
    connector = FlakyConnector(failures_before_success=10)
    runtime = _build_runtime(connector)
    extractor = runtime.extractor
    policy = runtime.policy_engine
    workflow = WorkflowState(tenant_id="tenant-a", submitted_by="user-1", request_text="Need 9 monitors for engineering")

    result = run_workflow_graph(extractor, policy, runtime, workflow)

    assert result.current_state == "dispatch_error"
    assert connector.attempts == 3
    assert len(connector.dispatched) == 0
    assert result.graph_metadata["dispatch_retry_counts"]
    assert any(entry["event"] == "approval.dispatch_failed_terminal" for entry in result.execution_log)