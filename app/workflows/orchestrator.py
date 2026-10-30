"""
StateGraph Orchestrator.

Compiles the graph and exposes a unified interface to run it.
"""
import logging
from typing import Dict, Any, Callable

# Load LangGraph safely
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    
# We use in-memory state persistence for early phases
memory_saver = MemorySaver() if LANGGRAPH_AVAILABLE else None
    
from app.workflows.state import AgenticState
from app.workflows.supervisor import supervisor_node

logger = logging.getLogger(__name__)


# ── Graph Nodes ──────────────────────────────────────────────────────────────
from app.agents.specialized_agents import (
    run_research_agent,
    run_analysis_agent,
    run_evaluation_agent
)
# ──────────────────────────────────────────────────────────────────────────────


def build_graph() -> Any:
    """Builds and compiles the StateGraph for execution."""
    if not LANGGRAPH_AVAILABLE:
        raise RuntimeError("langgraph is not installed. Run: pip install langgraph langchain-core")
        
    builder = StateGraph(AgenticState)
    
    # 1. Add nodes
    builder.add_node("Supervisor", supervisor_node.__call__)
    builder.add_node("ResearchAgent", run_research_agent)
    builder.add_node("AnalysisAgent", run_analysis_agent)
    builder.add_node("EvaluationAgent", run_evaluation_agent)
    
    # 2. Define edges
    # Standard entrypoint
    builder.set_entry_point("Supervisor")
    
    # Define conditional routing from the Supervisor based on the 'next_node' state field.
    # The supervisor decides where to go next.
    def supervisor_router(state: AgenticState) -> str:
        next_n = state.get("next_node", "END")
        if next_n == "END":
            return END
        return next_n
        
    builder.add_conditional_edges("Supervisor", supervisor_router)
    
    # Once a worker agent finishes, it ALWAYS returns control to the Supervisor 
    # to evaluate if more work is needed or if it should end.
    builder.add_edge("ResearchAgent", "Supervisor")
    builder.add_edge("AnalysisAgent", "Supervisor")
    builder.add_edge("EvaluationAgent", "Supervisor")
    
    # 3. Compile with memory persistence
    return builder.compile(checkpointer=memory_saver)

# Global cached graph
_graph_instance = None

def get_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph()
    return _graph_instance
