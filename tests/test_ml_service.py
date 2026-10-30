"""
Phase 5 — ML Service Tests.
Run with:   pytest tests/test_ml_service.py -v
"""

import pytest

from app.services.ml_service import MLService

@pytest.fixture(scope="module")
def ml():
    return MLService()


# ── Text Similarity ──────────────────────────────────────────────────────────

def test_text_similarity_identical(ml):
    text = "Machine learning engineer with Python and AWS experience."
    score = ml.calculate_text_similarity(text, text)
    # Identical texts should be exactly 1.0 (with slight float variance)
    assert 0.99 < score <= 1.0

def test_text_similarity_completely_different(ml):
    text1 = "I love baking chocolate chip cookies."
    text2 = "Machine learning engineer with Python and AWS experience."
    score = ml.calculate_text_similarity(text1, text2)
    # Should be close to 0
    assert 0.0 <= score < 0.1

def test_text_similarity_partial_match(ml):
    text1 = "We are looking for a Python backend developer."
    text2 = "I am a frontend developer but I know a little Python."
    score = ml.calculate_text_similarity(text1, text2)
    # Should be somewhere in the middle
    assert 0.1 < score < 0.9

def test_text_similarity_empty(ml):
    score = ml.calculate_text_similarity("", "Python developer")
    assert score == 0.0


# ── Skill Overlap ─────────────────────────────────────────────────────────────

def test_skill_overlap_perfect_match(ml):
    resume = ["Python", "AWS", "SQL"]
    job = ["Python", "AWS", "SQL"]
    result = ml.calculate_skill_overlap(resume, job)
    
    assert result["overlap_score"] == 1.0
    assert len(result["matched_skills"]) == 3
    assert len(result["missing_skills"]) == 0

def test_skill_overlap_partial(ml):
    resume = ["Python", "Pandas", "Scikit-learn"]
    job = ["Python", "SQL", "AWS"]
    result = ml.calculate_skill_overlap(resume, job)
    
    assert result["overlap_score"] == 0.333  # 1/3
    assert "Python" in result["matched_skills"]
    assert "SQL" in result["missing_skills"]
    assert "AWS" in result["missing_skills"]

def test_skill_overlap_missing_all(ml):
    resume = ["Java", "Spring"]
    job = ["Python", "FastAPI"]
    result = ml.calculate_skill_overlap(resume, job)
    
    assert result["overlap_score"] == 0.0
    assert len(result["matched_skills"]) == 0
    assert len(result["missing_skills"]) == 2

def test_skill_overlap_no_requirements(ml):
    resume = ["Python"]
    job = []
    result = ml.calculate_skill_overlap(resume, job)
    
    assert result["overlap_score"] == 0.0


# ── Overall Compatibility ─────────────────────────────────────────────────────

def test_overall_compatibility(ml):
    # 60% weight to skills, 40% to text sim
    score = ml.calculate_overall_compatibility(text_sim_score=0.5, skill_overlap_score=0.8, weight_skills=0.6)
    # (0.8 * 0.6) + (0.5 * 0.4) = 0.48 + 0.20 = 0.68
    assert score == 0.68

def test_overall_compatibility_fallback_weight(ml):
    # Tests that invalid weights fallback to 0.6
    score = ml.calculate_overall_compatibility(text_sim_score=0.5, skill_overlap_score=0.8, weight_skills=1.5)
    assert score == 0.68
