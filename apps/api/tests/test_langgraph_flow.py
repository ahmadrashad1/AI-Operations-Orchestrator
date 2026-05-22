from __future__ import annotations

from app.ai.extraction import RequestExtractionAgent
from app.ai.policy import PolicyEngine
from app.domain.models import WorkflowState
from app.orchestration import langgraph_adapter
from app.orchestration.langgraph_adapter import run_workflow_graph
from app.orchestration.runtime import WorkflowRuntime
from app.services.audit import AuditService


class MockConnector:
    name = "slack"

    def __init__(self) -> None:
        self.dispatched: list[dict[str, object]] = []

    def authenticate(self) -> bool:
        return True

    def validate(self, payload) -> bool:
        return True

    def execute(self, payload, idempotency_key):
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


class FakeLangGraphModule:
    class Graph:
        def __init__(self) -> None:
            self.nodes = []


def test_langgraph_adapter_runs_graph_flow(monkeypatch) -> None:
    monkeypatch.setattr(langgraph_adapter, "langgraph", FakeLangGraphModule())

    extractor = RequestExtractionAgent()
    settings = type("S", (), {"manager_approval_threshold": 3000.0, "finance_approval_threshold": 5000.0})()
    policy = PolicyEngine(settings=settings)
    audit = AuditService(repository=MemoryAuditRepository())
    connector = MockConnector()

    runtime = WorkflowRuntime(
        extractor=extractor,
        policy_engine=policy,
        audit_service=audit,
        connector_registry=MockRegistry(connector),
        job_queue=None,
    )

    workflow = WorkflowState(tenant_id="tenant-a", submitted_by="user-1", request_text="Need 5 laptops for engineering")

    result = run_workflow_graph(extractor, policy, runtime, workflow)

    assert result.status == result.status.__class__.waiting_approval
    assert result.current_state == "awaiting_approval"
    assert [approval.role for approval in result.approvals] == ["Manager", "Finance"]
    assert len(connector.dispatched) == 2
    assert any(entry["event"] == "request.extracted" for entry in result.execution_log)
    assert any(entry["event"] == "policy.evaluated" for entry in result.execution_log)