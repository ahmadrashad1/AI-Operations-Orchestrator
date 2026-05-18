from app.domain.models import WorkflowState
from app.ai.extraction import RequestExtractionAgent
from app.ai.policy import PolicyEngine
from app.services.audit import AuditService
from app.services.workflows import WorkflowService
from app.orchestration.runtime import WorkflowRuntime


class MockConnector:
    name = "slack"

    def __init__(self):
        self.dispatched = []

    def authenticate(self):
        return True

    def validate(self, payload):
        return True

    def execute(self, payload, idempotency_key):
        self.dispatched.append({"payload": payload, "idempotency_key": idempotency_key})
        return type("D", (), {"model_dump": lambda self: {"status": "queued", "idempotency_key": idempotency_key}})()


class MockRegistry:
    def __init__(self, connector):
        self._connectors = {connector.name: connector}

    def get(self, name: str):
        return self._connectors.get(name)


def test_graph_execution_and_dispatch():
    extractor = RequestExtractionAgent()
    settings = type("S", (), {"manager_approval_threshold": 3000.0, "finance_approval_threshold": 5000.0})()
    policy = PolicyEngine(settings=settings)
    audit = AuditService(repository=type("R", (), {"append": lambda *_: None})())

    mock = MockConnector()
    runtime = WorkflowRuntime(
        extractor=extractor,
        policy_engine=policy,
        audit_service=audit,
        connector_registry=MockRegistry(mock),
        job_queue=None,
    )

    wf = WorkflowState(tenant_id="t1", submitted_by="u1", request_text="Need 3 laptops for engineering")
    wf = runtime.bootstrap(wf)

    # After bootstrap, approvals should be built (Manager/Finance depending on cost)
    assert wf.status in (wf.status.__class__.waiting_approval, wf.status.__class__.completed)
    # If approvals exist, mock connector should have been called synchronously
    if wf.approvals:
        assert len(mock.dispatched) == len(wf.approvals)
