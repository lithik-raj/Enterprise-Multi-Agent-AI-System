"""
Phase 18 — Machine Learning Training Pipeline & Model Artifact Tests.

Validates Section 17 of the Master Prompt:
- Dataset loading and validation
- Feature engineering (TF-IDF cosine similarity, skill overlap, Jaccard, length ratios)
- Model training, evaluation metrics (R², MAE, Accuracy, F1)
- Model artifact serialization (.joblib) and metadata JSON
- Production inference engine with confidence scoring and feature contributions
- Integration with ML tools and agents
"""

from pathlib import Path
import pytest

from app.ml.train import (
    load_dataset,
    train_and_save_model,
    CompatibilityPipeline,
    DEFAULT_DATASET_PATH,
    MODEL_FILE_PATH,
    METADATA_FILE_PATH,
)
from app.ml.inference import get_ml_inference_engine
from app.services.ml_service import get_ml_service
from app.tools.ml_tools import run_ml_prediction, MLPredictionInput


def test_dataset_exists_and_valid():
    """Verify labeled dataset exists and contains required feature columns and rows."""
    assert DEFAULT_DATASET_PATH.exists(), "Dataset file must exist at data/datasets/resume_job_pairs.csv"
    r_texts, j_texts, r_skills, j_skills, scores, labels = load_dataset(DEFAULT_DATASET_PATH)

    assert len(r_texts) >= 15, "Dataset must contain at least 15 training pairs"
    assert len(scores) == len(r_texts)
    assert len(labels) == len(r_texts)
    assert all(0.0 <= s <= 1.0 for s in scores), "All compatibility scores must be between 0.0 and 1.0"
    assert set(labels).issubset({0, 1}), "Labels must be binary (0 or 1)"


def test_model_training_and_evaluation_metrics():
    """Verify model trains cleanly and produces strong evaluation metrics."""
    pipeline, metrics = train_and_save_model()

    assert metrics.samples_count >= 15
    assert metrics.r2_score >= 0.85, f"R² score should be >= 0.85, got {metrics.r2_score}"
    assert metrics.mean_absolute_error <= 0.10, f"MAE should be <= 0.10, got {metrics.mean_absolute_error}"
    assert metrics.classification_accuracy >= 0.80, f"Accuracy should be >= 80%, got {metrics.classification_accuracy}"
    assert metrics.f1_score >= 0.80, f"F1 should be >= 0.80, got {metrics.f1_score}"

    # Verify feature importances sum to approximately 1.0
    importances = metrics.feature_importances
    assert "tfidf_cosine_similarity" in importances
    assert "skill_overlap_ratio" in importances
    assert sum(importances.values()) == pytest.approx(1.0, abs=0.05)


def test_model_artifacts_saved():
    """Verify .joblib model and metadata JSON files exist on disk."""
    assert MODEL_FILE_PATH.exists(), "Trained model artifact compatibility_model.joblib must exist"
    assert METADATA_FILE_PATH.exists(), "Model metadata JSON must exist"
    assert MODEL_FILE_PATH.stat().st_size > 10000, "Model file size should be > 10KB"


def test_inference_engine_strong_match():
    """Verify inference engine correctly scores a strong AI/ML match."""
    engine = get_ml_inference_engine()
    assert engine.is_available is True

    res = engine.predict(
        resume_text="Senior Machine Learning Engineer with 4 years building PyTorch deep learning models, FastAPI APIs, and Docker.",
        job_text="Seeking AI/ML Engineer proficient in Python, PyTorch, Deep Learning, Docker, and FastAPI microservices.",
        resume_skills=["Python", "PyTorch", "Deep Learning", "Docker", "FastAPI"],
        job_skills=["Python", "PyTorch", "Deep Learning", "Docker", "FastAPI"],
    )

    assert res["predicted_score"] >= 0.80
    assert res["is_match"] is True
    assert res["match_category"] == "Strong Match"
    assert res["confidence"] >= 0.70
    assert "tfidf_cosine_similarity" in res["features"]
    assert "skill_overlap_ratio" in res["features"]


def test_inference_engine_weak_match():
    """Verify inference engine correctly scores a disjoint role."""
    engine = get_ml_inference_engine()

    res = engine.predict(
        resume_text="Graphic designer and Illustrator skilled in Photoshop, Figma, and typography.",
        job_text="Seeking Senior AI Engineer to build distributed PyTorch neural networks and Kubernetes pipelines.",
        resume_skills=["Photoshop", "Figma", "Illustrator"],
        job_skills=["Python", "PyTorch", "Kubernetes", "Deep Learning"],
    )

    assert res["predicted_score"] <= 0.50
    assert res["is_match"] is False
    assert res["match_category"] == "Low Match"


def test_ml_service_and_tool_integration():
    """Verify MLService and run_ml_prediction tool incorporate the trained model."""
    ml_svc = get_ml_service()
    pred = ml_svc.predict_trained_model(
        resume_text="NLP Engineer with spaCy and HuggingFace transformers.",
        job_text="Hiring NLP Engineer for spaCy text classification.",
        resume_skills=["Python", "spaCy", "Transformers", "NLP"],
        job_skills=["Python", "spaCy", "NLP"],
    )
    assert "predicted_score" in pred
    assert "features" in pred

    tool_out = run_ml_prediction(MLPredictionInput(
        resume_skills=["Python", "Machine Learning", "NLP"],
        job_skills=["Python", "Machine Learning", "NLP", "LangGraph"],
        resume_text="Experienced in Python, Machine Learning, and NLP models.",
        job_text="Requires Python, Machine Learning, NLP, and LangGraph.",
    ))
    assert tool_out.overall_compatibility > 0.0
    assert tool_out.model_prediction is not None
    assert "predicted_score" in tool_out.model_prediction
