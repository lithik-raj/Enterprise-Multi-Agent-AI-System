"""
Phase 8 — LangGraph tests.
Run with:   pytest tests/test_workflows.py -v
"""

import pytest
from unittest.mock import patch, MagicMock

from app.workflows.state import AgenticState, AgentStep
from app.workflows.orchestrator import _graph_instance, build_graph
import app.workflows.orchestrator as orch

def test_state_schema():
    state: AgenticState = {
        "task_input": "Analyze this repo",
        "document_ids": ["doc1"],
        "steps": [],
        "next_node": "",
        "final_answer": "",
        "evaluation_score": 0.0,
        "evaluation_feedback": "",
        "context": {}
    }
    
    step = AgentStep(agent_name="Research", action="gather", result="Done")
    state["steps"].append(step)
    
    assert len(state["steps"]) == 1
    assert state["steps"][0].agent_name == "Research"


def test_supervisor_routing_logic():
    from app.workflows.supervisor import SupervisorNode
    supervisor = SupervisorNode()
    
    # 1. Zero steps -> Should route to ResearchAgent
    state_start = {"steps": []}
    update = supervisor(state_start)
    assert update["next_node"] == "ResearchAgent"
    
    # 2. After Research -> Should route to AnalysisAgent
    step1 = AgentStep(agent_name="ResearchAgent", action="x", result="y")
    state_after_research = {"steps": [step1]}
    update = supervisor(state_after_research)
    assert update["next_node"] == "AnalysisAgent"
    
    # 3. After Analysis -> Should route to EvaluationAgent
    step2 = AgentStep(agent_name="AnalysisAgent", action="x", result="y")
    state_after_analysis = {"steps": [step1, step2]}
    update = supervisor(state_after_analysis)
    assert update["next_node"] == "EvaluationAgent"
    
    # 4. After Evaluation -> Should route to END
    step3 = AgentStep(agent_name="EvaluationAgent", action="x", result="y")
    state_after_eval = {"steps": [step1, step2, step3]}
    update = supervisor(state_after_eval)
    assert update["next_node"] == "END"


@pytest.mark.skipif(not orch.LANGGRAPH_AVAILABLE, reason="LangGraph not installed")
@patch("app.agents.specialized_agents.get_llm_service")
@patch("app.agents.specialized_agents.retrieve_context_tool")
def test_graph_compilation_and_execution(mock_retrieve, mock_get_llm):
    """
    Tests compiling the graph and running the actual agents via LangGraph.
    """
    # Setup mocks for LLM to avoid API key requirement in tests
    mock_llm = MagicMock()
    mock_resp1 = MagicMock()
    mock_resp1.content = "Analysis Result"
    mock_resp2 = MagicMock()
    mock_resp2.content = "9.5/10 - Great job"
    
    # generate() is called twice: once for analysis, once for evaluation
    mock_llm.generate.side_effect = [mock_resp1, mock_resp2]
    mock_get_llm.return_value = mock_llm
    
    # Mock RAG retrieval
    mock_retrieve.return_value = "--- Excerpt 1 ---\nContext info."
    
    graph = build_graph()
    
    # Run the graph
    initial_state = {
        "task_input": "Test Graph",
        "document_ids": [],
        "steps": [],
        "next_node": "",
        "final_answer": "",
        "evaluation_score": 0.0,
        "evaluation_feedback": "",
        "context": {}
    }
    
    config = {"configurable": {"thread_id": "test_workflow_01"}}
    # Let langgraph execute until END
    final_state = graph.invoke(initial_state, config)
    
    # The supervisor should have routed through all three agents.
    assert len(final_state["steps"]) == 3
    assert final_state["steps"][0].agent_name == "ResearchAgent"
    assert final_state["steps"][1].agent_name == "AnalysisAgent"
    assert final_state["steps"][2].agent_name == "EvaluationAgent"
    
    assert final_state["final_answer"] == "Analysis Result"
    assert "9.5/10" in final_state["evaluation_feedback"]
