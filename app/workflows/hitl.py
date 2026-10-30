"""
Human-in-the-Loop (HITL) helpers.

Wraps LangGraph's checkpointer to pause a workflow and wait for human
approval before continuing. Used by the /api/approval endpoint.

Pattern:
  1. Graph is compiled with `interrupt_before=["EvaluationAgent"]`
  2. First invoke() runs Research -> Analysis, then pauses.
  3. The task state + pending node are surfaced to the user via the API.
  4. Human approves or rejects via POST /api/approval.
  5. On approval, invoke() is called again on the same thread_id with an
     empty input — the graph resumes from the saved checkpoint.
  6. On rejection, the thread is abandoned (or a cancel step is appended).
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Nodes that require human sign-off before execution
APPROVAL_REQUIRED_NODES = ["EvaluationAgent"]


def build_hitl_graph():
    """
    Builds a version of the StateGraph that pauses before EvaluationAgent,
    so a human can inspect the AnalysisAgent output before evaluation runs.
    """
    try:
        from langgraph.graph import StateGraph, END
        from langgraph.checkpoint.memory import MemorySaver
    except ImportError:
        raise RuntimeError("langgraph is not installed.")

    from app.workflows.state import AgenticState
    from app.workflows.supervisor import supervisor_node
    from app.agents.specialized_agents import (
        run_research_agent,
        run_analysis_agent,
        run_evaluation_agent,
    )

    builder = StateGraph(AgenticState)
    builder.add_node("Supervisor", supervisor_node.__call__)
    builder.add_node("ResearchAgent", run_research_agent)
    builder.add_node("AnalysisAgent", run_analysis_agent)
    builder.add_node("EvaluationAgent", run_evaluation_agent)

    builder.set_entry_point("Supervisor")

    def supervisor_router(state: AgenticState) -> str:
        next_n = state.get("next_node", "END")
        if next_n == "END":
            return END
        return next_n

    builder.add_conditional_edges("Supervisor", supervisor_router)
    builder.add_edge("ResearchAgent", "Supervisor")
    builder.add_edge("AnalysisAgent", "Supervisor")
    builder.add_edge("EvaluationAgent", "Supervisor")

    memory = MemorySaver()
    # interrupt_before causes LangGraph to pause BEFORE running EvaluationAgent
    return builder.compile(checkpointer=memory, interrupt_before=["EvaluationAgent"])


def get_pending_approval_state(graph: Any, thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Inspects a paused graph thread and returns the current state if it is
    waiting for human approval, otherwise returns None.
    """
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = graph.get_state(config)
        # If there are tasks pending (next nodes to run), the graph is paused
        if snapshot and snapshot.next:
            return {
                "thread_id": thread_id,
                "pending_node": list(snapshot.next),
                "current_state": {
                    "task_input": snapshot.values.get("task_input", ""),
                    "final_answer": snapshot.values.get("final_answer", ""),
                    "steps_completed": len(snapshot.values.get("steps", [])),
                }
            }
    except Exception as e:
        logger.error("Could not inspect graph state for thread %s: %s", thread_id, e)
    return None


def resume_graph(graph: Any, thread_id: str) -> Dict[str, Any]:
    """
    Resumes a paused graph thread after human approval.
    Passes None as input so LangGraph continues from the saved checkpoint.
    """
    config = {"configurable": {"thread_id": thread_id}}
    final_state = graph.invoke(None, config)
    return final_state


# Module-level singleton for the HITL graph
_hitl_graph = None


def get_hitl_graph():
    global _hitl_graph
    if _hitl_graph is None:
        _hitl_graph = build_hitl_graph()
    return _hitl_graph
