"""
ML Agent.

Responsibilities:
- Resume & job description semantic similarity.
- Skill overlap quantification.
- Ranking and compatibility scoring.
- Skill-gap analysis.
- Clear mathematical explainability of results.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.workflows.state import AgenticState, AgentStep
from app.tools.ml_tools import run_ml_prediction, MLPredictionInput

logger = logging.getLogger(__name__)


def run_ml_agent(state: AgenticState) -> Dict[str, Any]:
    """
    ML Agent Node.
    Computes mathematical compatibility using TF-IDF cosine similarity and skill overlap ratios.
    """
    task = state.get("task_input", "")
    ctx = state.get("context", {})
    nlp_data = ctx.get("nlp_analysis", {})

    candidate_skills = nlp_data.get("candidate_skills", ["Python", "Machine Learning", "NLP", "SQL"])
    benchmark_skills = nlp_data.get("benchmark_skills", ["Python", "Machine Learning", "NLP", "LangGraph", "Vector Databases", "RAG"])

    logger.info("MLAgent calculating compatibility for %d candidate skills", len(candidate_skills))

    # Execute run_ml_prediction tool
    pred = run_ml_prediction(
        MLPredictionInput(
            resume_skills=candidate_skills,
            job_skills=benchmark_skills,
            resume_text=task + " " + " ".join(candidate_skills),
            job_text=" ".join(benchmark_skills),
            weight_skills=0.6,
        )
    )

    step = AgentStep(
        agent_name="MLAgent",
        action="compatibility_prediction_and_gap_ranking",
        result=(
            f"Computed {pred.overall_compatibility:.1f}% compatibility ({pred.ranking_category}). "
            f"TF-IDF: {pred.semantic_similarity_score:.2f}, Overlap: {pred.skill_overlap_score:.2f}."
        ),
        status="completed",
    )

    updated_ctx = dict(ctx)
    updated_ctx["ml_analysis"] = pred.model_dump()

    return {
        "steps": [step],
        "next_node": "rag_agent",
        "context": updated_ctx,
    }
