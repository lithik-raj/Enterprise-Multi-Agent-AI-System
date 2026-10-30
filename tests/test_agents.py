"""
Phase 9 — Specialized Agents tests.
Run with:   pytest tests/test_agents.py -v
"""

from unittest.mock import patch, MagicMock

from app.workflows.state import AgenticState
from app.agents.specialized_agents import (
    run_research_agent,
    run_analysis_agent,
    run_evaluation_agent
)


def test_research_agent_updates_state():
    state: AgenticState = {
        "task_input": "Who is the CEO?",
        "document_ids": [],
        "steps": [],
        "next_node": "",
        "final_answer": "",
        "evaluation_score": 0.0,
        "evaluation_feedback": "",
        "context": {}
    }
    
    with patch("app.agents.specialized_agents.retrieve_context_tool") as mock_retrieve:
        mock_retrieve.return_value = "--- Excerpt 1 ---\nCEO is Alice."
        
        new_state = run_research_agent(state)
        
        assert "steps" in new_state
        assert len(new_state["steps"]) == 1
        assert new_state["steps"][0].agent_name == "ResearchAgent"
        assert new_state["context"]["retrieved_documents"] == "--- Excerpt 1 ---\nCEO is Alice."


def test_analysis_agent_updates_state():
    state: AgenticState = {
        "task_input": "Summarize.",
        "document_ids": [],
        "steps": [],
        "next_node": "",
        "final_answer": "",
        "evaluation_score": 0.0,
        "evaluation_feedback": "",
        "context": {"retrieved_documents": "CEO is Alice"}
    }
    
    with patch("app.agents.specialized_agents.get_llm_service") as mock_get_llm:
        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = "Alice is the leader."
        mock_llm.generate.return_value = mock_resp
        mock_get_llm.return_value = mock_llm
        
        new_state = run_analysis_agent(state)
        
        assert "steps" in new_state
        assert len(new_state["steps"]) == 1
        assert new_state["steps"][0].agent_name == "AnalysisAgent"
        assert new_state["final_answer"] == "Alice is the leader."


def test_evaluation_agent_updates_state():
    state: AgenticState = {
        "task_input": "Summarize.",
        "document_ids": [],
        "steps": [],
        "next_node": "",
        "final_answer": "Alice is the leader.",
        "evaluation_score": 0.0,
        "evaluation_feedback": "",
        "context": {}
    }
    
    with patch("app.agents.specialized_agents.get_llm_service") as mock_get_llm:
        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = "9.5/10 - Great job."
        mock_llm.generate.return_value = mock_resp
        mock_get_llm.return_value = mock_llm
        
        new_state = run_evaluation_agent(state)
        
        assert "steps" in new_state
        assert len(new_state["steps"]) == 1
        assert new_state["steps"][0].agent_name == "EvaluationAgent"
        assert new_state["evaluation_score"] == 0.85
        assert new_state["evaluation_feedback"] == "9.5/10 - Great job."
