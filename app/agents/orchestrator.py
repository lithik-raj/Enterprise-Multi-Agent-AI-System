"""
Orchestrator Agent.

Responsibilities:
- Receive user task.
- Understand intent and scope.
- Break down the task into an execution plan.
- Decide which specialized agents are required.
- Identify potential consequential actions requiring Human-in-the-Loop review.
- Maintain and coordinate workflow state.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from datetime import datetime

from app.workflows.state import AgenticState, AgentStep
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

CONSEQUENTIAL_KEYWORDS = [
    "submit application", "submit job application", "send application",
    "dispatch application", "send outbound email", "dispatch email",
    "send message to recruiter", "contact recruiter", "reach out to hiring",
    "prepare application message and submit"
]


def run_orchestrator(state: AgenticState) -> Dict[str, Any]:
    """
    Orchestrator Node.
    Decomposes the task, determines necessary agents, and initializes execution state.
    """
    task = state.get("task_input", "")
    doc_ids = state.get("document_ids", [])
    logger.info("Orchestrator analyzing task: '%s' (docs=%s)", task, doc_ids)

    # Detect if task involves consequential external actions
    task_lower = task.lower()
    requires_hitl = any(kw in task_lower for kw in CONSEQUENTIAL_KEYWORDS)

    # Determine needed agents based on user intent
    planned_agents = ["research_agent", "nlp_agent", "ml_agent", "rag_agent", "recommendation_agent", "evaluation_agent"]

    plan = {
        "intent": "Career & Technical Opportunity Match Assessment",
        "subtasks": [
            "1. Research company background and tech stack",
            "2. Extract NLP skills and entity metadata from profile and job description",
            "3. Compute TF-IDF cosine similarity, skill overlap, and compatibility score",
            "4. Retrieve grounded learning chunks from knowledge base via RAG",
            "5. Synthesize structured recommendations and high-impact project idea",
            "6. Evaluate groundedness, completeness, and safety guardrails",
        ],
        "requires_hitl": requires_hitl,
        "planned_agents": planned_agents,
        "timestamp": datetime.utcnow().isoformat(),
    }

    step = AgentStep(
        agent_name="OrchestratorAgent",
        action="task_planning_and_decomposition",
        result=f"Decomposed task into {len(planned_agents)} agent phases. HITL required: {requires_hitl}.",
        status="completed",
    )

    # Update context
    ctx = dict(state.get("context", {}))
    ctx["plan"] = plan
    ctx["hitl_required"] = requires_hitl

    return {
        "steps": [step],
        "next_node": "research_agent",
        "context": ctx,
    }
