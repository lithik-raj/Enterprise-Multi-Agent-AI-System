"""
Phase 19 — ML Model API Endpoint Tests.

Validates the trained model REST API:
  POST /api/ml/predict   — real-time inference with feature breakdowns
  GET  /api/ml/metadata  — training metrics and feature importances
  Input validation       — rejects malformed requests
  Regression             — health endpoint still operational
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


# ── POST /api/ml/predict ──────────────────────────────────────────────────────

async def test_ml_predict_strong_match(client):
    """A highly compatible resume/job pair should return is_match=True."""
    resp = await client.post("/api/ml/predict", json={
        "resume_text": "Senior Python ML Engineer with 5 years experience in PyTorch, Deep Learning, FastAPI, and Docker deployments.",
        "job_text": "Seeking ML Engineer with Python, PyTorch, Deep Learning, FastAPI, Docker, and production deployment experience.",
        "resume_skills": ["Python", "PyTorch", "Deep Learning", "FastAPI", "Docker"],
        "job_skills": ["Python", "PyTorch", "Deep Learning", "FastAPI", "Docker"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["predicted_score"] >= 0.75
    assert body["is_match"] is True
    assert body["match_category"] == "Strong Match"
    assert body["confidence"] >= 0.60
    assert "tfidf_cosine_similarity" in body["features"] or "skill_overlap_ratio" in body["features"]
    assert "timestamp" in body


async def test_ml_predict_weak_match(client):
    """A mismatched profile should return is_match=False."""
    resp = await client.post("/api/ml/predict", json={
        "resume_text": "Graphic designer and Illustrator working with Photoshop, Figma, and visual branding.",
        "job_text": "Seeking Senior AI Engineer to build distributed PyTorch neural networks on Kubernetes.",
        "resume_skills": ["Photoshop", "Figma", "Illustrator"],
        "job_skills": ["Python", "PyTorch", "Kubernetes", "Deep Learning"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["predicted_score"] <= 0.55
    assert body["is_match"] is False
    assert body["match_category"] == "Low Match"


async def test_ml_predict_returns_features(client):
    """Prediction response must include engineered feature values."""
    resp = await client.post("/api/ml/predict", json={
        "resume_text": "Data scientist with Python, Pandas, and Scikit-learn experience.",
        "job_text": "Seeking Data Scientist with Python, Pandas, and machine learning skills.",
        "resume_skills": ["Python", "Pandas", "Scikit-learn"],
        "job_skills": ["Python", "Pandas", "Machine Learning"],
    })
    assert resp.status_code == 200
    features = resp.json()["features"]
    assert isinstance(features, dict)
    assert len(features) >= 2


async def test_ml_predict_rejects_empty_resume_text(client):
    """Too-short resume_text must be rejected by Pydantic validation."""
    resp = await client.post("/api/ml/predict", json={
        "resume_text": "short",
        "job_text": "Seeking AI Engineer with Python and Machine Learning expertise.",
        "resume_skills": ["Python"],
        "job_skills": ["Python"],
    })
    assert resp.status_code == 422


async def test_ml_predict_rejects_empty_skills(client):
    """Empty skill lists must be rejected."""
    resp = await client.post("/api/ml/predict", json={
        "resume_text": "Experienced software engineer with full stack development skills.",
        "job_text": "Seeking senior backend engineer with production microservice experience.",
        "resume_skills": [],
        "job_skills": ["Python"],
    })
    assert resp.status_code == 422


# ── GET /api/ml/metadata ──────────────────────────────────────────────────────

async def test_ml_metadata_returns_training_metrics(client):
    """Metadata endpoint must return valid training evaluation metrics."""
    resp = await client.get("/api/ml/metadata")
    assert resp.status_code == 200
    body = resp.json()

    assert body["samples_count"] >= 15
    assert body["r2_score"] >= 0.80
    assert body["classification_accuracy"] >= 0.80
    assert body["f1_score"] >= 0.80
    assert "tfidf_cosine_similarity" in body["feature_importances"]
    assert "skill_overlap_ratio" in body["feature_importances"]
    assert body["model_file_exists"] is True
    assert body["metadata_file_exists"] is True
    assert len(body["feature_names"]) == 5


# ── Regression ────────────────────────────────────────────────────────────────

async def test_health_still_ok(client):
    """Health endpoint must remain operational after Phase 19 changes."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
