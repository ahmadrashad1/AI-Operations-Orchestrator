"""LangGraph adapter for workflow orchestration.

The runtime uses a real LangGraph state graph when the dependency is available.
If LangGraph cannot be imported, it falls back to the existing linear executor.
"""
from __future__ import annotations

from typing import Any

try:
    from langgraph.graph import END, START, StateGraph  # type: ignore
except Exception:  # pragma: no cover - optional
    StateGraph = None
    START = END = None

from app.orchestration.graph import build_default_graph
from app.domain.models import WorkflowState


MAX_DISPATCH_RETRIES = 2


def _retry_key(approval_id: str) -> str:
    return f"dispatch:{approval_id}"


def _ensure_graph_metadata(workflow: WorkflowState) -> dict[str, Any]:
    workflow.graph_metadata.setdefault("dispatch_index", 0)
    workflow.graph_metadata.setdefault("dispatch_errors", {})
    workflow.graph_metadata.setdefault("dispatch_retry_counts", {})
    workflow.graph_metadata.setdefault("dispatch_retry_limit", MAX_DISPATCH_RETRIES)
    return workflow.graph_metadata


def build_langgraph_workflow(extractor, policy_engine, runtime):
    if StateGraph is None:
        return None

    graph = StateGraph(WorkflowState)

    def node_extract(workflow: WorkflowState) -> WorkflowState:
        workflow.extraction = extractor.extract(workflow.request_text)
        workflow.execution_log.append(
            {"event": "request.extracted", "workflow_state": workflow.current_state}
        )
        runtime.audit_service.log(
            workflow_id=workflow.workflow_id,
            actor="procurement-agent",
            action="request.extracted",
            metadata=workflow.extraction.model_dump(),
        )
        return workflow

    def node_policy(workflow: WorkflowState) -> WorkflowState:
        if workflow.extraction is None:
            raise ValueError("Workflow extraction must exist before policy evaluation")

        workflow.policy_results = policy_engine.evaluate(workflow.extraction)
        workflow.current_state = "policy_evaluated"
        workflow.execution_log.append(
            {"event": "policy.evaluated", "reasons": workflow.policy_results.reasons}
        )
        runtime.audit_service.log(
            workflow_id=workflow.workflow_id,
            actor="policy-engine",
            action="policy.evaluated",
            metadata=workflow.policy_results.model_dump(),
        )
        return workflow

    def node_plan_approvals(workflow: WorkflowState) -> WorkflowState:
        approvals = runtime._build_approvals(workflow)
        workflow.approvals = approvals

        if approvals:
            workflow.status = workflow.status.__class__.waiting_approval
            workflow.current_state = "awaiting_approval"
            workflow.execution_log.append(
                {
                    "event": "approvals.planned",
                    "approval_roles": [approval.role for approval in approvals],
                }
            )
        else:
            workflow.status = workflow.status.__class__.completed
            workflow.current_state = "completed"
            workflow.execution_log.append({"event": "workflow.completed", "mode": "auto-approved"})
            runtime.audit_service.log(
                workflow_id=workflow.workflow_id,
                actor="orchestrator",
                action="workflow.completed",
                metadata={"mode": "auto-approved"},
            )
        return workflow

    def node_dispatch(workflow: WorkflowState) -> WorkflowState:
        metadata = _ensure_graph_metadata(workflow)
        approvals = workflow.approvals
        dispatch_index = int(metadata.get("dispatch_index", 0))

        while dispatch_index < len(approvals):
            approval = approvals[dispatch_index]
            try:
                runtime._dispatch_approval_request(workflow=workflow, approval=approval)
            except Exception as exc:
                approval_key = _retry_key(approval.approval_id)
                retry_counts: dict[str, int] = metadata["dispatch_retry_counts"]
                retry_count = retry_counts.get(approval_key, 0) + 1
                retry_counts[approval_key] = retry_count
                metadata["dispatch_errors"][approval_key] = str(exc)
                metadata["dispatch_index"] = dispatch_index
                workflow.current_state = "dispatch_failed"
                workflow.execution_log.append(
                    {
                        "event": "approval.dispatch_failed",
                        "approval_id": approval.approval_id,
                        "role": approval.role,
                        "error": str(exc),
                        "retry_count": retry_count,
                    }
                )
                runtime.audit_service.log(
                    workflow_id=workflow.workflow_id,
                    actor="slack",
                    action="approval.dispatch_failed",
                    metadata={
                        "approval_id": approval.approval_id,
                        "role": approval.role,
                        "error": str(exc),
                        "retry_count": retry_count,
                    },
                )
                return workflow

            workflow.execution_log.append(
                {
                    "event": "approval.dispatch_succeeded",
                    "approval_id": approval.approval_id,
                    "role": approval.role,
                    "index": dispatch_index,
                }
            )
            dispatch_index += 1
            metadata["dispatch_index"] = dispatch_index

        metadata.pop("dispatch_errors", None)
        workflow.current_state = "dispatch_completed"
        return workflow

    def node_retry(workflow: WorkflowState) -> WorkflowState:
        metadata = _ensure_graph_metadata(workflow)
        if not metadata.get("dispatch_errors"):
            return workflow

        approval_key, error_message = next(iter(metadata["dispatch_errors"].items()))
        retry_counts: dict[str, int] = metadata["dispatch_retry_counts"]
        retry_count = retry_counts.get(approval_key, 0)
        workflow.execution_log.append(
            {
                "event": "approval.dispatch_retry_scheduled",
                "approval_key": approval_key,
                "error": error_message,
                "retry_count": retry_count,
            }
        )
        runtime.audit_service.log(
            workflow_id=workflow.workflow_id,
            actor="orchestrator",
            action="approval.dispatch_retry_scheduled",
            metadata={
                "approval_key": approval_key,
                "error": error_message,
                "retry_count": retry_count,
            },
        )
        workflow.current_state = "dispatch_retrying"
        return workflow

    def node_error(workflow: WorkflowState) -> WorkflowState:
        metadata = _ensure_graph_metadata(workflow)
        approval_key, error_message = next(iter(metadata["dispatch_errors"].items()))
        workflow.current_state = "dispatch_error"
        workflow.execution_log.append(
            {
                "event": "approval.dispatch_failed_terminal",
                "approval_key": approval_key,
                "error": error_message,
            }
        )
        runtime.audit_service.log(
            workflow_id=workflow.workflow_id,
            actor="orchestrator",
            action="approval.dispatch_failed_terminal",
            metadata={"approval_key": approval_key, "error": error_message},
        )
        return workflow

    def route_after_plan(workflow: WorkflowState) -> str:
        return "dispatch" if workflow.approvals else "complete"

    def route_after_dispatch(workflow: WorkflowState) -> str:
        metadata = _ensure_graph_metadata(workflow)
        if metadata.get("dispatch_errors"):
            approval_key = next(iter(metadata["dispatch_errors"]))
            retry_count = metadata["dispatch_retry_counts"].get(approval_key, 0)
            if retry_count <= metadata["dispatch_retry_limit"]:
                return "retry"
            return "error"

        if int(metadata.get("dispatch_index", 0)) < len(workflow.approvals):
            return "dispatch"
        return "complete"

    graph.add_node("extract_request", node_extract)
    graph.add_node("evaluate_policy", node_policy)
    graph.add_node("plan_approvals", node_plan_approvals)
    graph.add_node("dispatch_approvals", node_dispatch)
    graph.add_node("retry_dispatch", node_retry)
    graph.add_node("dispatch_error", node_error)
    graph.add_node("complete", lambda workflow: workflow)

    graph.add_edge(START, "extract_request")
    graph.add_edge("extract_request", "evaluate_policy")
    graph.add_edge("evaluate_policy", "plan_approvals")
    graph.add_conditional_edges(
        "plan_approvals",
        route_after_plan,
        {
            "dispatch": "dispatch_approvals",
            "complete": "complete",
        },
    )
    graph.add_conditional_edges(
        "dispatch_approvals",
        route_after_dispatch,
        {
            "dispatch": "dispatch_approvals",
            "retry": "retry_dispatch",
            "error": "dispatch_error",
            "complete": "complete",
        },
    )
    graph.add_edge("retry_dispatch", "dispatch_approvals")
    graph.add_edge("dispatch_error", END)
    graph.add_edge("complete", END)

    return graph.compile()


def run_workflow_graph(extractor, policy_engine, runtime, workflow: WorkflowState) -> WorkflowState:
    compiled_graph = build_langgraph_workflow(extractor, policy_engine, runtime)
    if compiled_graph is not None:
        result = compiled_graph.invoke(workflow)
        if isinstance(result, WorkflowState):
            return result
        return WorkflowState.model_validate(result)

    return build_default_graph(extractor, policy_engine, runtime).run(workflow)
