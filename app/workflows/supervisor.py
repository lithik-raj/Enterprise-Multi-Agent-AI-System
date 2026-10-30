"""
Supervisor Node.

The supervisor's job is to look at the current state, decide what needs to happen next, 
and set the `next_node` in the state.
"""

import logging
import json
from typing import Dict, Any

from app.workflows.state import AgenticState, AgentStep
from app.services.llm_service import get_llm_service
from app.services.prompt_templates import get_template

logger = logging.getLogger(__name__)

class SupervisorNode:
    def __init__(self):
        # The supervisor uses the LLM to make routing decisions
        # In a real app we might fallback to logic if the LLM is down.
        pass
        
    def __call__(self, state: AgenticState) -> Dict[str, Any]:
        """
        Executes the supervisor logic.
        Returns a dict representing updates to the state.
        """
        steps = state.get("steps", [])
        
        # Simple logical routing for Phase 8 / early phases:
        # If no steps have been executed, route to the ResearchAgent
        # This will be replaced by LLM-based routing later.
        
        if not steps:
            logger.info("Supervisor routing to ResearchAgent (start of task)")
            return {"next_node": "ResearchAgent"}
            
        last_step = steps[-1]
        
        if last_step.agent_name == "ResearchAgent":
            # After research, route to writer/analyst
            return {"next_node": "AnalysisAgent"}
            
        if last_step.agent_name == "AnalysisAgent":
            # After analysis, route to evaluator
            return {"next_node": "EvaluationAgent"}
            
        if last_step.agent_name == "EvaluationAgent":
            # After evaluation, if score is high enough or loop limit reached, finish.
            # We'll default to END for now.
            return {"next_node": "END"}
            
        # Fallback
        return {"next_node": "END"}
        
# For direct node binding
supervisor_node = SupervisorNode()
