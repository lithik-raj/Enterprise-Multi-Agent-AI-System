"""
Evaluation Agent.

Responsibilities:
- Evaluate generated outputs for relevance, completeness, and groundedness.
- Detect potential hallucination by comparing output against retrieved RAG chunks.
- Verify task completion against original user request.
- Apply automated safety guardrails.
- Return structured evaluation data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.workflows.state import AgenticState, AgentStep
from app.services.evaluation_service import get_evaluation_service

logger = logging.getLogger(__name__)


def run_evaluation_agent(state: AgenticState) -> Dict[str, Any]:
    """
    Evaluation Agent Node.
    Scores generated content across groundedness, relevance, and completeness dimensions.
    """
    task = state.get("task_input", "")
    final_answer = state.get("final_answer", "")
    ctx = state.get("context", {})
    rag_context = ctx.get("retrieved_documents", "")

    logger.info("EvaluationAgent assessing output quality (length=%d)", len(final_answer))
    evaluator = get_evaluation_service()

    eval_result = evaluator.evaluate(
        task=task,
        answer=final_answer,
        context=rag_context,
    )

    overall_score = round(
        (eval_result.relevance + eval_result.completeness + eval_result.groundedness) / 3.0,
        2,
    )

    feedback_text = (
        f"Automated Multi-Agent Evaluation: Groundedness={eval_result.groundedness:.2f}, "
        f"Relevance={eval_result.relevance:.2f}, Completeness={eval_result.completeness:.2f}. "
        f"Task Completed: {eval_result.task_completed}. Issues: {len(eval_result.issues)} detected."
    )

    step = AgentStep(
        agent_name="EvaluationAgent",
        action="quality_and_groundedness_evaluation",
        result=f"Verified generation quality: score {overall_score:.2f}/1.00 ({len(eval_result.issues)} issues).",
        status="completed",
    )

    updated_ctx = dict(ctx)
    updated_ctx["evaluation"] = {
        "relevance": eval_result.relevance,
        "completeness": eval_result.completeness,
        "groundedness": eval_result.groundedness,
        "task_completed": eval_result.task_completed,
        "issues": eval_result.issues,
        "overall_score": overall_score,
    }

    return {
        "steps": [step],
        "evaluation_score": overall_score,
        "evaluation_feedback": feedback_text,
        "next_node": "END",
        "context": updated_ctx,
    }
