"""
ML Model API Router — Phase 19.

Exposes the trained scikit-learn Resume-Job Compatibility Model via REST endpoints:

  POST /api/ml/predict   — Run real-time inference with feature breakdowns
  GET  /api/ml/metadata  — Return training metrics and feature importances
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.ml.inference import get_ml_inference_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ml", tags=["Machine Learning"])

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
METADATA_PATH = WORKSPACE_ROOT / "models" / "model_metadata.json"


# ── Request / Response Schemas ────────────────────────────────────────────────

class MLPredictRequest(BaseModel):
    """Input for the trained ML compatibility model."""

    resume_text: str = Field(
        ..., min_length=10, max_length=10000,
        description="Full text of the candidate's resume.",
    )
    job_text: str = Field(
        ..., min_length=10, max_length=10000,
        description="Full text of the target job description.",
    )
    resume_skills: List[str] = Field(
        ..., min_length=1,
        description="Skills extracted from the resume.",
    )
    job_skills: List[str] = Field(
        ..., min_length=1,
        description="Skills required by the job posting.",
    )


class MLPredictResponse(BaseModel):
    """Output from the trained ML compatibility model."""

    predicted_score: float = Field(..., description="Compatibility score (0.0 – 1.0)")
    match_category: str = Field(..., description="Strong Match or Low Match")
    is_match: bool = Field(..., description="Whether the candidate meets the threshold")
    confidence: float = Field(..., description="Classifier confidence (0.0 – 1.0)")
    features: Dict[str, float] = Field(..., description="Engineered feature values used for prediction")
    model_available: bool = Field(..., description="Whether the trained .joblib model was used")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MLMetadataResponse(BaseModel):
    """Training metrics and feature importances from the saved model."""

    samples_count: int
    r2_score: float
    mean_absolute_error: float
    root_mean_squared_error: float
    classification_accuracy: float
    f1_score: float
    feature_names: List[str]
    feature_importances: Dict[str, float]
    model_file_exists: bool
    metadata_file_exists: bool


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/predict",
    response_model=MLPredictResponse,
    summary="Run real-time inference using the trained compatibility model",
)
async def ml_predict(request: MLPredictRequest) -> MLPredictResponse:
    """
    Accepts resume text, job text, and skill lists; returns a trained-model
    compatibility prediction with confidence score and feature contributions.
    """
    engine = get_ml_inference_engine()

    result = engine.predict(
        resume_text=request.resume_text,
        job_text=request.job_text,
        resume_skills=request.resume_skills,
        job_skills=request.job_skills,
    )

    return MLPredictResponse(
        predicted_score=result["predicted_score"],
        match_category=result["match_category"],
        is_match=result["is_match"],
        confidence=result["confidence"],
        features=result["features"],
        model_available=engine.is_available,
    )


@router.get(
    "/metadata",
    response_model=MLMetadataResponse,
    summary="Return training metrics and feature importances",
)
async def ml_metadata() -> MLMetadataResponse:
    """
    Returns the metadata from the most recent model training run,
    including R², MAE, accuracy, F1, and per-feature importances.
    """
    model_exists = (WORKSPACE_ROOT / "models" / "compatibility_model.joblib").exists()
    meta_exists = METADATA_PATH.exists()

    if not meta_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model metadata not found. Run `python scripts/train_ml_model.py` first.",
        )

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    return MLMetadataResponse(
        samples_count=meta["samples_count"],
        r2_score=meta["r2_score"],
        mean_absolute_error=meta["mean_absolute_error"],
        root_mean_squared_error=meta["root_mean_squared_error"],
        classification_accuracy=meta["classification_accuracy"],
        f1_score=meta["f1_score"],
        feature_names=meta["feature_names"],
        feature_importances=meta["feature_importances"],
        model_file_exists=model_exists,
        metadata_file_exists=meta_exists,
    )


@router.get(
    "/benchmark",
    summary="Return multi-paradigm model evaluation benchmark metrics",
)
async def ml_benchmark() -> Dict[str, Any]:
    """
    Returns quantitative comparative benchmark results across Heuristic Baseline,
    Trained Scikit-Learn (GBR), and LLM-as-a-Judge evaluators.
    """
    benchmark_file = WORKSPACE_ROOT / "data" / "benchmarks" / "model_benchmark_report.json"
    if benchmark_file.exists():
        with open(benchmark_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # Compute on-demand if report has not been generated yet
    from scripts.benchmark_evaluation import run_benchmark
    return run_benchmark()

