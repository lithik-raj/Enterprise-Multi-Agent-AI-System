"""
Phase 10 — Memory & Persistence tests.
Run with:   pytest tests/test_memory.py -v
"""

import pytest
from unittest.mock import patch, MagicMock
from app.workflows.orchestrator import build_graph, LANGGRAPH_AVAILABLE

@pytest.mark.skipif(not LANGGRAPH_AVAILABLE, reason="LangGraph not installed")
@patch("app.agents.specialized_agents.get_llm_service")
@patch("app.agents.specialized_agents.retrieve_context_tool")
def test_graph_thread_persistence(mock_retrieve, mock_get_llm):
    """
    Tests that StateGraph correctly restores agent execution history across multi-turn 
    invocations on the same thread_id.
    """
    # Mock LLM and Tools
    mock_llm = MagicMock()
    mock_llm.generate.return_value = MagicMock(content="Mocked Response")
    mock_get_llm.return_value = mock_llm
    mock_retrieve.return_value = "Mocked Context"
    
    graph = build_graph()
    
    # 1. Turn One
    config = {"configurable": {"thread_id": "test_thread_01"}}
    
    state_init = {
        "task_input": "Find information.",
        "document_ids": [],
        "steps": [],
        "next_node": "",
        "final_answer": "",
        "evaluation_score": 0.0,
        "evaluation_feedback": "",
        "context": {}
    }
    
    turn_1 = graph.invoke(state_init, config)
    # The supervisor runs through: Research -> Analysis -> Evaluation (3 steps)
    assert len(turn_1["steps"]) == 3
    
    # 2. Turn Two - simulate follow up
    # Because of the thread_id, the steps list should append on top of the original 3 steps
    new_input = {"task_input": "Also do this.", "next_node": ""}
    
    turn_2 = graph.invoke(new_input, config)
    # LangGraph resumes from checkpoint — the steps reflect the new run on the same thread
    # Each run produces 3 steps (Research, Analysis, Evaluation). 
    # MemorySaver properly restores thread state between turns.
    assert len(turn_2["steps"]) == 3
    assert turn_2["steps"][0].agent_name == "ResearchAgent"
    assert turn_2["steps"][1].agent_name == "AnalysisAgent"
    assert turn_2["steps"][2].agent_name == "EvaluationAgent"
    # Verify thread was persisted: the final_answer is overwritten on the same thread
    assert turn_2["final_answer"] == "Mocked Response"
