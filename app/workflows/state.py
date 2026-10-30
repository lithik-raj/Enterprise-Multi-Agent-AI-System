"""
Agentic State schema.

Defines the state structure that is passed between nodes in LangGraph.
"""

from typing import Annotated, Dict, Any, List, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

# We use operator.add to append strings to lists natively in langgraph state if needed
import operator

class AgentStep(BaseModel):
    agent_name: str
    action: str
    result: str
    status: str = "completed"
    
class AgenticState(TypedDict):
    # The original task input (e.g. session id or full text)
    task_input: str
    
    # Task metadata (e.g. document IDs to restrict to)
    document_ids: List[str]
    
    # Track the steps taken by each agent
    # Annotated with operator.add means LangGraph will append rather than overwrite
    steps: Annotated[List[AgentStep], operator.add]
    
    # Supervisor decides the next node to route to
    next_node: str
    
    # Final result string
    final_answer: str
    
    # Optional evaluation metrics
    evaluation_score: float
    evaluation_feedback: str
    
    # Shared memory context map
    context: Dict[str, Any]
