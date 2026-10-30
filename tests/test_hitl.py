"""
Phase 12 — Human-in-the-Loop tests.
Run with:   pytest tests/test_hitl.py -v
"""
import pytest
from unittest.mock import patch, MagicMock

try:
    from langgraph.graph import StateGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

from app.workflows.hitl import (
    build_hitl_graph,
    get_pending_approval_state,
    resume_graph,
    APPROVAL_REQUIRED_NODES,
)


def test_approval_required_nodes_defined():
    assert "EvaluationAgent" in APPROVAL_REQUIRED_NODES


@pytest.mark.skipif(not LANGGRAPH_AVAILABLE, reason="LangGraph not installed")
@patch("app.agents.specialized_agents.get_llm_service")
@patch("app.agents.specialized_agents.retrieve_context_tool")
def test_hitl_graph_pauses_before_evaluation(mock_retrieve, mock_get_llm):
    """
    When a HITL graph runs, it should pause AFTER AnalysisAgent
    and BEFORE EvaluationAgent, waiting for human approval.
    """
    mock_llm = MagicMock()
    mock_llm.generate.return_value = MagicMock(content="Analysis output")
    mock_get_llm.return_value = mock_llm
    mock_retrieve.return_value = "Some context"

    graph = build_hitl_graph()
    config = {"configurable": {"thread_id": "hitl_test_01"}}

    state = {
        "task_input": "Review my resume.",
        "document_ids": [],
        "steps": [],
        "next_node": "",
        "final_answer": "",
        "evaluation_score": 0.0,
        "evaluation_feedback": "",
        "context": {}
    }

    # Run graph — it should pause before EvaluationAgent
    result = graph.invoke(state, config)

    # At the pause point, steps should contain Research + Analysis (2 steps)
    assert len(result["steps"]) == 2
    assert result["steps"][0].agent_name == "ResearchAgent"
    assert result["steps"][1].agent_name == "AnalysisAgent"

    # The graph yields the answer but hasn't evaluated yet
    assert result["final_answer"] == "Analysis output"


@pytest.mark.skipif(not LANGGRAPH_AVAILABLE, reason="LangGraph not installed")
@patch("app.agents.specialized_agents.get_llm_service")
@patch("app.agents.specialized_agents.retrieve_context_tool")
def test_hitl_inspect_paused_state(mock_retrieve, mock_get_llm):
    """After pausing, get_pending_approval_state should surface the pending node."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = MagicMock(content="Draft answer")
    mock_get_llm.return_value = mock_llm
    mock_retrieve.return_value = "context"

    graph = build_hitl_graph()
    thread_id = "hitl_inspect_01"
    config = {"configurable": {"thread_id": thread_id}}

    state = {
        "task_input": "Analyse the doc.",
        "document_ids": [],
        "steps": [],
        "next_node": "",
        "final_answer": "",
        "evaluation_score": 0.0,
        "evaluation_feedback": "",
        "context": {}
    }
    graph.invoke(state, config)

    approval_info = get_pending_approval_state(graph, thread_id)
    assert approval_info is not None
    assert "EvaluationAgent" in approval_info["pending_node"]
    assert approval_info["current_state"]["final_answer"] == "Draft answer"


@pytest.mark.skipif(not LANGGRAPH_AVAILABLE, reason="LangGraph not installed")
@patch("app.agents.specialized_agents.get_llm_service")
@patch("app.agents.specialized_agents.retrieve_context_tool")
def test_hitl_resume_after_approval(mock_retrieve, mock_get_llm):
    """
    After approval, resume_graph() should complete the remaining EvaluationAgent step.
    """
    mock_llm = MagicMock()
    mock_llm.generate.return_value = MagicMock(content="Final evaluated response")
    mock_get_llm.return_value = mock_llm
    mock_retrieve.return_value = "context"

    graph = build_hitl_graph()
    thread_id = "hitl_resume_01"
    config = {"configurable": {"thread_id": thread_id}}

    state = {
        "task_input": "Evaluate my resume.",
        "document_ids": [],
        "steps": [],
        "next_node": "",
        "final_answer": "",
        "evaluation_score": 0.0,
        "evaluation_feedback": "",
        "context": {}
    }
    graph.invoke(state, config)   # pauses before EvaluationAgent

    # Human approves — resume the graph
    final = resume_graph(graph, thread_id)

    # Now all 3 steps should be complete
    assert len(final["steps"]) == 3
    assert final["steps"][2].agent_name == "EvaluationAgent"
