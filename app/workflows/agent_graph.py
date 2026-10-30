"""
Integrated Multi-Agent Graph.

Implements the complete 7-agent enterprise intelligence pipeline using LangGraph:
Orchestrator -> ResearchAgent -> NLPAgent -> MLAgent -> RAGAgent -> RecommendationAgent -> EvaluationAgent -> END.

Maintains workflow state in AgenticState and supports MemorySaver checkpointing
and interrupt_before for Human-in-the-Loop governance.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    END = "__end__"
    MemorySaver = None

from app.workflows.state import AgenticState, AgentStep
from app.agents.orchestrator import run_orchestrator
from app.agents.research_agent import run_research_agent
from app.agents.nlp_agent import run_nlp_agent
from app.agents.ml_agent import run_ml_agent
from app.agents.rag_agent import run_rag_agent
from app.agents.recommendation_agent import run_recommendation_agent
from app.agents.evaluation_agent import run_evaluation_agent

# Default checkpointer
_checkpointer = MemorySaver() if LANGGRAPH_AVAILABLE else None


def build_integrated_agent_graph(
    checkpointer: Any = None,
    interrupt_before: Optional[List[str]] = None,
) -> Any:
    """
    Builds and compiles the complete 7-agent LangGraph StateGraph.
    """
    if not LANGGRAPH_AVAILABLE:
        raise RuntimeError("LangGraph is not available. Please install langgraph.")

    builder = StateGraph(AgenticState)

    # 1. Add all 7 core agents as nodes
    builder.add_node("Orchestrator", run_orchestrator)
    builder.add_node("ResearchAgent", run_research_agent)
    builder.add_node("NLPAgent", run_nlp_agent)
    builder.add_node("MLAgent", run_ml_agent)
    builder.add_node("RAGAgent", run_rag_agent)
    builder.add_node("RecommendationAgent", run_recommendation_agent)
    builder.add_node("EvaluationAgent", run_evaluation_agent)

    # 2. Wire the sequential decision-support pipeline
    builder.set_entry_point("Orchestrator")
    builder.add_edge("Orchestrator", "ResearchAgent")
    builder.add_edge("ResearchAgent", "NLPAgent")
    builder.add_edge("NLPAgent", "MLAgent")
    builder.add_edge("MLAgent", "RAGAgent")
    builder.add_edge("RAGAgent", "RecommendationAgent")
    builder.add_edge("RecommendationAgent", "EvaluationAgent")
    builder.add_edge("EvaluationAgent", END)

    # 3. Compile with checkpointer and optional interrupt points for HITL
    active_checkpointer = checkpointer if checkpointer is not None else _checkpointer
    compiled = builder.compile(
        checkpointer=active_checkpointer,
        interrupt_before=interrupt_before or [],
    )
    logger.info("Integrated 7-agent LangGraph StateGraph compiled successfully")
    return compiled


# Cached singleton instance
_integrated_graph = None


def get_integrated_graph() -> Any:
    global _integrated_graph
    if _integrated_graph is None and LANGGRAPH_AVAILABLE:
        _integrated_graph = build_integrated_agent_graph()
    return _integrated_graph


def run_integrated_pipeline(
    task_input: str,
    document_ids: Optional[List[str]] = None,
    thread_id: Optional[str] = None,
    step_callback: Optional[callable] = None,
) -> Dict[str, Any]:
    """
    Execute the integrated 7-agent pipeline.
    Works either via LangGraph invoke or graceful direct step runner for test flexibility.
    """
    tid = thread_id or "default_session"
    initial_state: AgenticState = {
        "task_input": task_input,
        "document_ids": document_ids or [],
        "steps": [],
        "next_node": "",
        "final_answer": "",
        "evaluation_score": 0.0,
        "evaluation_feedback": "",
        "context": {},
    }

    if LANGGRAPH_AVAILABLE:
        try:
            graph = get_integrated_graph()
            config = {"configurable": {"thread_id": tid}}
            result = graph.invoke(initial_state, config)
            return result
        except Exception as exc:
            logger.warning("LangGraph execution encountered exception: %s. Running direct fallback pipeline.", exc)

    # Deterministic direct fallback pipeline runner:
    # Executes each agent node in sequence, collecting steps and enriching state
    current_state = dict(initial_state)

    nodes = [
        ("Orchestrator", run_orchestrator),
        ("ResearchAgent", run_research_agent),
        ("NLPAgent", run_nlp_agent),
        ("MLAgent", run_ml_agent),
        ("RAGAgent", run_rag_agent),
        ("RecommendationAgent", run_recommendation_agent),
        ("EvaluationAgent", run_evaluation_agent),
    ]

    for name, node_fn in nodes:
        update = node_fn(current_state)
        # Append steps
        if "steps" in update:
            current_state["steps"].extend(update["steps"])
            if step_callback:
                for s in update["steps"]:
                    step_callback(s)
        # Update context
        if "context" in update:
            current_state["context"].update(update["context"])
        # Update final answer
        if "final_answer" in update:
            current_state["final_answer"] = update["final_answer"]
        # Update evaluation
        if "evaluation_score" in update:
            current_state["evaluation_score"] = update["evaluation_score"]
        if "evaluation_feedback" in update:
            current_state["evaluation_feedback"] = update["evaluation_feedback"]
        if "next_node" in update:
            current_state["next_node"] = update["next_node"]

    return current_state
