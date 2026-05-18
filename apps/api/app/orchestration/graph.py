"""Simple LangGraph-like executor shim for Phase 2.

This module provides a compact, testable graph executor that sequences
extraction -> policy -> approval building -> dispatch. It is designed as
an adapter so we can later swap a real LangGraph implementation.
"""

from __future__ import annotations

from collections.abc import Callable

from app.domain.models import WorkflowState


class GraphNode:
    def __init__(self, name: str, func: Callable[[WorkflowState], WorkflowState]):
        self.name = name
        self.func = func


class GraphExecutor:
    """Execute a linear graph of nodes against a workflow state."""

    def __init__(self) -> None:
        self.nodes: list[GraphNode] = []

    def add_node(self, name: str, func: Callable[[WorkflowState], WorkflowState]) -> None:
        self.nodes.append(GraphNode(name, func))

    def run(self, workflow: WorkflowState) -> WorkflowState:
        """Run all nodes in order, mutating and returning the workflow."""
        for node in self.nodes:
            workflow = node.func(workflow)
        return workflow


def build_default_graph(extractor, policy_engine, runtime) -> GraphExecutor:
    """Build the default graph using provided components.

    Nodes:
    - extract: call extractor.extract
    - evaluate_policy: call policy_engine.evaluate
    - build_approvals: runtime._build_approvals
    - dispatch: runtime._dispatch_approval_request for each approval (queues dispatch)
    """

    def node_extract(wf: WorkflowState) -> WorkflowState:
        wf.extraction = extractor.extract(wf.request_text)
        wf.execution_log.append({"event": "request.extracted", "workflow_state": wf.current_state})
        runtime.audit_service.log(
            workflow_id=wf.workflow_id,
            actor="procurement-agent",
            action="request.extracted",
            metadata=wf.extraction.model_dump(),
            tenant_id=wf.tenant_id,
        )
        return wf

    def node_policy(wf: WorkflowState) -> WorkflowState:
        wf.policy_results = policy_engine.evaluate(wf.extraction)
        wf.current_state = "policy_evaluated"
        wf.execution_log.append({"event": "policy.evaluated", "reasons": wf.policy_results.reasons})
        runtime.audit_service.log(
            workflow_id=wf.workflow_id,
            actor="policy-engine",
            action="policy.evaluated",
            metadata=wf.policy_results.model_dump(),
            tenant_id=wf.tenant_id,
        )
        return wf

    def node_build_approvals(wf: WorkflowState) -> WorkflowState:
        approvals = runtime._build_approvals(wf)
        if approvals:
            wf.approvals.extend(approvals)
            wf.status = (
                wf.status.__class__.waiting_approval
                if hasattr(wf.status, "waiting_approval")
                else wf.status
            )
            wf.current_state = "awaiting_approval"
        else:
            wf.status = (
                wf.status.__class__.completed if hasattr(wf.status, "completed") else wf.status
            )
            wf.current_state = "completed"
            runtime.audit_service.log(
                workflow_id=wf.workflow_id,
                actor="orchestrator",
                action="workflow.completed",
                metadata={"mode": "auto-approved"},
                tenant_id=wf.tenant_id,
            )
        return wf

    def node_dispatch(wf: WorkflowState) -> WorkflowState:
        for approval in wf.approvals:
            runtime._dispatch_approval_request(workflow=wf, approval=approval)
        return wf

    executor = GraphExecutor()
    executor.add_node("extract", node_extract)
    executor.add_node("evaluate_policy", node_policy)
    executor.add_node("build_approvals", node_build_approvals)
    executor.add_node("dispatch", node_dispatch)
    return executor
