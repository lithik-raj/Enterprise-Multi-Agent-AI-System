"""
Machine Learning Tools.

Provides verified ML tools for computing TF-IDF similarity, skill overlap,
gap analysis, and overall candidate-job compatibility scoring.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from app.services.ml_service import get_ml_service

logger = logging.getLogger(__name__)


class SimilarityInput(BaseModel):
    text1: str = Field(..., description="First text block (e.g. resume)")
    text2: str = Field(..., description="Second text block (e.g. job description)")


class SimilarityOutput(BaseModel):
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    algorithm: str = "TF-IDF Vectorization with Cosine Similarity"
    explanation: str


class MLPredictionInput(BaseModel):
    resume_skills: List[str] = Field(..., description="Skills extracted from candidate profile")
    job_skills: List[str] = Field(..., description="Skills required by the job posting")
    resume_text: Optional[str] = Field("", description="Full text of candidate resume")
    job_text: Optional[str] = Field("", description="Full text of job posting")
    weight_skills: float = Field(0.6, ge=0.0, le=1.0, description="Weight given to skill overlap vs semantic similarity")


class MLPredictionOutput(BaseModel):
    overall_compatibility: float = Field(..., description="Calculated match percentage (0-100%)")
    skill_overlap_score: float
    semantic_similarity_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    ranking_category: str
    formula_explanation: str
    model_prediction: Optional[dict] = Field(default=None, description="Detailed predictions from trained ML model")


def calculate_similarity(input_data: SimilarityInput) -> SimilarityOutput:
    """
    Calculate mathematical cosine similarity between two texts using TF-IDF representation.
    """
    logger.info("Executing calculate_similarity tool")
    ml = get_ml_service()
    score = ml.calculate_text_similarity(input_data.text1, input_data.text2)

    return SimilarityOutput(
        similarity_score=round(score, 4),
        algorithm="TF-IDF Vectorization with Cosine Similarity",
        explanation=f"Calculated TF-IDF vector cosine angle yielding a semantic closeness of {score*100:.1f}%.",
    )


def run_ml_prediction(input_data: MLPredictionInput) -> MLPredictionOutput:
    """
    Run the end-to-end ML compatibility evaluation model.
    Combines skill overlap coefficient with text cosine similarity.
    """
    logger.info("Executing run_ml_prediction tool for %d candidate skills vs %d job skills",
                len(input_data.resume_skills), len(input_data.job_skills))
    ml = get_ml_service()

    # 1. Skill overlap calculation
    overlap_res = ml.calculate_skill_overlap(input_data.resume_skills, input_data.job_skills)
    overlap_score = overlap_res.get("overlap_score", 0.0)
    matched = overlap_res.get("matched_skills", [])
    missing = overlap_res.get("missing_skills", [])

    # 2. Text similarity
    text_sim = 0.0
    if input_data.resume_text and input_data.job_text:
        text_sim = ml.calculate_text_similarity(input_data.resume_text, input_data.job_text)
    else:
        # Fall back to skill representations
        text_sim = ml.calculate_text_similarity(" ".join(input_data.resume_skills), " ".join(input_data.job_skills))

    # 3. Overall weighted compatibility
    overall = ml.calculate_overall_compatibility(
        text_sim_score=text_sim,
        skill_overlap_score=overlap_score,
        weight_skills=input_data.weight_skills,
    )
    percent_score = round(overall * 100, 1)

    # 4. Categorical ranking
    if percent_score >= 80.0:
        ranking = "Strong Match (High Interview Probability)"
    elif percent_score >= 60.0:
        ranking = "Moderate Match (Targeted Upskilling Required)"
    else:
        ranking = "Significant Gap (Core Prerequisites Missing)"

    formula = (
        f"Overall Match ({percent_score}%) = [{input_data.weight_skills} * Skill Overlap ({overlap_score*100:.1f}%)] + "
        f"[{1.0 - input_data.weight_skills:.1f} * TF-IDF Similarity ({text_sim*100:.1f}%)]"
    )

    # 5. Trained model prediction
    trained_pred = ml.predict_trained_model(
        resume_text=input_data.resume_text or " ".join(input_data.resume_skills),
        job_text=input_data.job_text or " ".join(input_data.job_skills),
        resume_skills=input_data.resume_skills,
        job_skills=input_data.job_skills,
    )

    return MLPredictionOutput(
        overall_compatibility=percent_score,
        skill_overlap_score=round(overlap_score, 4),
        semantic_similarity_score=round(text_sim, 4),
        matched_skills=matched,
        missing_skills=missing,
        ranking_category=ranking,
        formula_explanation=formula,
        model_prediction=trained_pred,
    )

