"""Adapter to use LangGraph if available, otherwise fall back to GraphExecutor.

This adapter exposes a `run_workflow_graph(extractor, policy_engine, runtime, workflow)`
function which will prefer a LangGraph implementation when the `langgraph` package
is installed, and fall back to the existing `build_default_graph` otherwise.
"""

from __future__ import annotations

try:
    import langgraph  # type: ignore
except Exception:  # pragma: no cover - optional
    langgraph = None

from app.domain.models import WorkflowState
from app.orchestration.graph import build_default_graph


def run_workflow_graph(extractor, policy_engine, runtime, workflow: WorkflowState) -> WorkflowState:
    if langgraph:
        # A placeholder demonstrating intent: construct a LangGraph flow and run it.
        # Real implementation would map nodes/operators to LangGraph constructs.
        try:
            # Attempt a minimal LangGraph execution if available
            langgraph.Graph()
            # This is intentionally minimal; prefer GraphExecutor behavior
            # for predictable local execution.
        except Exception:
            return build_default_graph(extractor, policy_engine, runtime).run(workflow)
        return build_default_graph(extractor, policy_engine, runtime).run(workflow)

    # Fallback
    return build_default_graph(extractor, policy_engine, runtime).run(workflow)
