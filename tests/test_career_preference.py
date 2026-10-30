"""
tests/test_career_preference.py

Test Suite for Career Preference & Live Hiring Matching Service & API.
Verifies location preference selection, real company data, campus visuals,
multi-criteria ranking, and API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.career_preference_service import (
    get_career_preference_service,
    CareerPreferenceRequest,
)

client = TestClient(app)

SAMPLE_AI_RESUME = """
ALEXANDER V. CHEN
AI & Machine Learning Systems Engineer | San Francisco, CA
chen.alexander@example.com | linkedin.com/in/alexander-chen-ai | github.com/alexchen-ai

SUMMARY:
Results-driven AI/ML Engineer with extensive experience in Python, PyTorch, LangGraph, RAG pipelines,
FAISS vector databases, and FastAPI microservices. Led end-to-end deployment of generative AI swarms.

SKILLS:
- Languages: Python, Java, SQL, C++, Bash
- Frameworks: PyTorch, TensorFlow, Hugging Face Transformers, Scikit-learn, LangGraph, FAISS, Docker
- Backend: FastAPI, REST APIs, Git, Linux, Docker, PostgreSQL

EXPERIENCE:
AI Systems Engineer at Synthetix AI Labs (2023 - Present)
- Architected multi-agent RAG retrieval systems in LangGraph and FAISS.
- Deployed FastAPI containerized microservices reducing latency by 42%.
- Integrated model evaluation guardrails for grounded responses.
"""


def test_service_get_locations():
    svc = get_career_preference_service()
    locs = svc.get_locations()
    assert len(locs) >= 8
    ids = [l.id for l in locs]
    assert "bengaluru" in ids
    assert "hyderabad" in ids
    assert "remote" in ids
    assert "san_francisco" in ids


def test_service_get_companies():
    svc = get_career_preference_service()
    companies = svc.get_companies()
    assert len(companies) >= 6
    names = [c.name.lower() for c in companies]
    assert any("google" in n for n in names)
    assert any("microsoft" in n for n in names)
    assert any("amazon" in n for n in names)
    assert any("ibm" in n for n in names)
    assert any("infosys" in n for n in names)
    for c in companies:
        assert c.logo_svg.startswith("<svg")
        assert c.campus_photo_svg.startswith("<svg")
        assert len(c.active_locations) > 0


def test_service_match_preferences_bengaluru():
    svc = get_career_preference_service()
    req = CareerPreferenceRequest(
        resume_text=SAMPLE_AI_RESUME,
        preferred_locations=["bengaluru"],
        work_mode="hybrid",
        target_role="ai_ml",
    )
    res = svc.match_preferences(req)
    assert res.total_live_jobs_scanned >= 10
    assert res.matched_jobs_count > 0
    top_match = res.matches[0]
    assert top_match.composite_score >= 70
    assert len(top_match.matched_skills) >= 2
    # Check that location score for Bengaluru job is high
    blr_matches = [m for m in res.matches if m.location_key == "bengaluru"]
    assert len(blr_matches) > 0
    assert blr_matches[0].location_score == 100


def test_service_match_preferences_remote():
    svc = get_career_preference_service()
    req = CareerPreferenceRequest(
        resume_text=SAMPLE_AI_RESUME,
        preferred_locations=["remote"],
        work_mode="remote",
        target_role="genai",
    )
    res = svc.match_preferences(req)
    assert res.matched_jobs_count > 0
    rem_matches = [m for m in res.matches if m.location_key == "remote"]
    assert len(rem_matches) > 0
    assert rem_matches[0].location_score >= 95


def test_api_get_locations():
    resp = client.get("/api/career/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 8
    keys = [item["id"] for item in data]
    assert "bengaluru" in keys


def test_api_get_companies():
    resp = client.get("/api/career/companies")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 6
    assert "logo_svg" in data[0]
    assert "campus_photo_svg" in data[0]


def test_api_get_live_jobs():
    resp = client.get("/api/career/live-jobs?location=bengaluru")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for j in data:
        assert j["location_key"] == "bengaluru"


def test_api_preference_match():
    resp = client.post(
        "/api/career/preference-match",
        json={
            "resume_text": SAMPLE_AI_RESUME,
            "preferred_locations": ["bengaluru", "hyderabad", "remote"],
            "work_mode": "hybrid",
            "target_role": "ai_ml",
            "min_match_score": 50,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_live_jobs_scanned"] >= 10
    assert data["matched_jobs_count"] > 0
    assert len(data["matches"]) > 0
    top = data["matches"][0]
    assert top["composite_score"] >= 65
    assert "company_logo_svg" in top
    assert "campus_photo_svg" in top
    assert "apply_url" in top
    assert "exact_address" in top
    assert len(top["exact_address"]) > 5


def test_api_upload_preference_match():
    # Test uploading a resume text file
    file_bytes = SAMPLE_AI_RESUME.encode("utf-8")
    resp = client.post(
        "/api/career/upload-preference-match",
        files={"file": ("alex_resume.txt", file_bytes, "text/plain")},
        data={
            "preferred_locations": "bengaluru,hyderabad,remote",
            "work_mode": "hybrid",
            "target_role": "ai_ml",
            "min_match_score": 45,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_jobs_count"] > 0
    assert len(data["matches"]) > 0
    assert "detected_candidate_locations" in data
    first_match = data["matches"][0]
    assert first_match["exact_address"]
    assert first_match["salary_range"]
    assert first_match["urgency_tag"]


def test_service_detect_locations_from_text():
    svc = get_career_preference_service()
    detected = svc.detect_locations_from_text(SAMPLE_AI_RESUME)
    assert "san_francisco" in detected


def test_api_preference_match_blank_fails():
    resp = client.post(
        "/api/career/preference-match",
        json={
            "resume_text": "short",
            "preferred_locations": ["bengaluru"],
        },
    )
    assert resp.status_code == 400


def test_api_apply_intent():
    resp = client.post(
        "/api/career/apply-intent",
        json={
            "job_id": "job-goog-blr-01",
            "company_name": "Google",
            "candidate_name": "Alexander Chen",
            "candidate_email": "alex@example.com",
            "preferred_location": "bengaluru",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "recorded"
    assert "google" in data["apply_url"].lower()


def test_service_get_locations_with_sites():
    svc = get_career_preference_service()
    locs = svc.get_locations()
    blr = next((l for l in locs if l.id == "bengaluru"), None)
    assert blr is not None
    assert len(blr.sites) >= 3
    assert any("Manyata" in s or "Bagmane" in s for s in blr.sites)


def test_service_detect_domain_from_text():
    svc = get_career_preference_service()
    domain, conf, breakdown, summary = svc.detect_domain_from_text(SAMPLE_AI_RESUME)
    assert "AI" in domain or "Generative" in domain
    assert conf >= 65
    assert len(breakdown) >= 4
    assert len(summary) > 10


def test_service_match_preferences_internships():
    svc = get_career_preference_service()
    req = CareerPreferenceRequest(
        resume_text=SAMPLE_AI_RESUME,
        preferred_locations=["bengaluru", "hyderabad", "remote"],
        opportunity_type="internship",
        work_mode="hybrid",
        target_role="ai_ml",
    )
    res = svc.match_preferences(req)
    assert res.matched_jobs_count > 0
    for m in res.matches:
        assert m.opportunity_type == "internship"
        assert "Internship" in m.opportunity_badge
        assert m.duration is not None
        assert len(m.duration) > 0


def test_service_match_preferences_jobs_only():
    svc = get_career_preference_service()
    req = CareerPreferenceRequest(
        resume_text=SAMPLE_AI_RESUME,
        preferred_locations=["bengaluru", "hyderabad"],
        opportunity_type="job",
        work_mode="hybrid",
        target_role="ai_ml",
    )
    res = svc.match_preferences(req)
    assert res.matched_jobs_count > 0
    for m in res.matches:
        assert m.opportunity_type == "job"
        assert "Full-Time" in m.opportunity_badge


def test_api_get_live_jobs_with_opportunity_type():
    resp = client.get("/api/career/live-jobs?opportunity_type=internship")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 5
    for item in data:
        assert item["opportunity_type"] == "internship"


def test_api_preference_match_with_internships():
    resp = client.post(
        "/api/career/preference-match",
        json={
            "resume_text": SAMPLE_AI_RESUME,
            "preferred_locations": ["bengaluru", "hyderabad"],
            "opportunity_type": "internship",
            "work_mode": "hybrid",
            "preferred_domain": "genai",
            "min_match_score": 40,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["opportunity_type_filter"] == "internship"
    assert "detected_domain" in data
    assert data["domain_confidence"] > 0
    assert len(data["matches"]) > 0
    first = data["matches"][0]
    assert first["opportunity_type"] == "internship"
    assert first["requisition_id"]
    assert first["domain_score"] >= 80


def test_api_upload_preference_match_with_internships():
    file_bytes = SAMPLE_AI_RESUME.encode("utf-8")
    resp = client.post(
        "/api/career/upload-preference-match",
        files={"file": ("candidate_profile.txt", file_bytes, "text/plain")},
        data={
            "preferred_locations": "bengaluru,pune,remote",
            "opportunity_type": "internship",
            "work_mode": "any",
            "preferred_domain": "genai",
            "min_match_score": 35,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["opportunity_type_filter"] == "internship"
    assert data["matched_jobs_count"] > 0
    assert data["matches"][0]["opportunity_type"] == "internship"


def test_service_campus_photo_urls():
    svc = get_career_preference_service()
    companies = svc.get_companies()
    assert len(companies) >= 8
    for comp in companies:
        assert comp.campus_photo_url.startswith("https://")
        assert len(comp.campus_photo_url) > 15
        assert comp.campus_photo_svg.startswith("<svg")

    req = CareerPreferenceRequest(
        resume_text=SAMPLE_AI_RESUME,
        preferred_locations=["bengaluru", "hyderabad", "san_francisco"],
    )
    res = svc.match_preferences(req)
    assert res.matched_jobs_count > 0
    for m in res.matches:
        assert m.campus_photo_url.startswith("https://")


