"""
app/ml/inference.py

Inference Service for the Trained Resume-Job Compatibility Model.
Loads the serialized CompatibilityPipeline artifact and produces real-time
compatibility predictions, match classification, and feature contribution scores.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_FILE_PATH = WORKSPACE_ROOT / "models" / "compatibility_model.joblib"


class MLInferenceEngine:
    """Production inference engine for compatibility scoring."""

    def __init__(self, model_path: Path = MODEL_FILE_PATH):
        self.model_path = model_path
        self.model = None
        self._load_attempted = False

    def _ensure_loaded(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True
        if self.model_path.exists():
            try:
                self.model = joblib.load(self.model_path)
                logger.info("Loaded trained compatibility model from: %s", self.model_path)
            except Exception as exc:
                logger.warning("Failed to load model from %s (%s). Falling back.", self.model_path, exc)
                self.model = None
        else:
            logger.info("Model file %s not found. Will use heuristic formula fallback.", self.model_path)
            self.model = None

    @property
    def is_available(self) -> bool:
        self._ensure_loaded()
        return self.model is not None

    def predict(
        self,
        resume_text: str,
        job_text: str,
        resume_skills: List[str],
        job_skills: List[str],
    ) -> Dict[str, Any]:
        """Generate prediction from the trained scikit-learn model."""
        self._ensure_loaded()
        if self.model is not None:
            try:
                return self.model.predict(
                    resume_text=resume_text,
                    job_text=job_text,
                    resume_skills=resume_skills,
                    job_skills=job_skills,
                )
            except Exception as exc:
                logger.error("Error during model inference: %s", exc)

        # Synchronized prediction via Unified Scoring Engine
        from app.services.scoring_engine import get_unified_scoring_engine
        eval_res = get_unified_scoring_engine().evaluate_candidate(
            resume_text=resume_text,
            target_role=job_text,
            job_description=job_text,
            explicit_candidate_skills=resume_skills,
            explicit_required_skills=job_skills,
        )

        return {
            "predicted_score": eval_res["predicted_score"],
            "match_category": eval_res["match_category"],
            "is_match": eval_res["is_match"],
            "confidence": eval_res["confidence"],
            "features": eval_res["features"],
        }


_engine_instance: Optional[MLInferenceEngine] = None


def get_ml_inference_engine() -> MLInferenceEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = MLInferenceEngine()
    return _engine_instance
