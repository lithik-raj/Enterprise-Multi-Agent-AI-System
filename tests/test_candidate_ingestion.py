"""
Test Suite for Autonomous HR Candidate Ingestion, Resume Upload & Zero-Key Voice Brain.
Validates:
- POST /api/batch/ingest-candidate
- POST /api/batch/upload-resume
- Zero-Key Dynamic Recruiter Voice Assistant Queries & Actions
"""

import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.batch_service import get_batch_service


@pytest.fixture
def client():
    return TestClient(app)


def test_ingest_candidate_json(client):
    """Test 1-Click candidate ingestion with text input."""
    payload = {
        "candidate_name": "Devi Ramanathan",
        "email": "devi.ramanathan@techcorp.in",
        "role": "Senior AI/ML Platform Engineer",
        "resume_text": (
            "Senior AI Engineer with 6.5 years experience building scalable LangGraph multi-agent systems, "
            "FAISS dense vector retrieval pipelines, PyTorch deep learning models, FastAPI microservices, "
            "and Docker Kubernetes orchestration in enterprise cloud environments."
        ),
        "auto_decide": True,
        "batch_id": "batch-demo-talent-001",
    }

    response = client.post("/api/batch/ingest-candidate", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "success"
    assert data["candidate_name"] == "Devi Ramanathan"
    assert "ingestion_result" in data
    res = data["ingestion_result"]

    assert res["predicted_score"] > 0
    assert "PyTorch" in res["matched_skills"] or "LangGraph" in res["matched_skills"] or "FastAPI" in res["matched_skills"]
    assert res["suggested_decision"] in ["OFFER_EXTENDED", "SHORTLISTED", "INTERVIEW_SCHEDULED", "REJECTED"]
    assert res["decision_committed"] is True
    assert "devi" in res["communicator_email_draft"].lower() or "dear" in res["communicator_email_draft"].lower()
    assert len(res["spoken_briefing"]) > 10

    # Verify candidate is now present in the batch leaderboard
    batch_resp = client.get("/api/batch/batch-demo-talent-001")
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    cand_names = [c["name"] for c in batch_data["leaderboard"]]
    assert "Devi Ramanathan" in cand_names


def test_upload_resume_file(client):
    """Test candidate ingestion via document file upload (TXT/MD)."""
    resume_content = b"""
    Karthik Sundaram
    karthik.sundaram@aimail.com
    Experience: 5 years in Machine Learning and Generative AI.
    Skills: Python, Scikit-Learn, PyTorch, LangGraph, Docker, SQL, FastAPI, AWS.
    Built automated retrieval-augmented generation pipelines and deployed distributed models.
    """

    file_obj = io.BytesIO(resume_content)
    files = {"file": ("karthik_resume.txt", file_obj, "text/plain")}
    data = {
        "role": "Senior AI/ML Platform Engineer",
        "candidate_name": "Karthik Sundaram",
        "auto_decide": "true",
        "batch_id": "batch-demo-talent-001",
    }

    response = client.post("/api/batch/upload-resume", data=data, files=files)
    assert response.status_code == 200, response.text
    resp_data = response.json()

    assert resp_data["status"] == "success"
    assert resp_data["candidate_name"] == "Karthik Sundaram"
    assert resp_data["ingestion_result"]["predicted_score"] > 0.5


def test_zero_key_voice_assistant(client):
    """Verify voice assistant operates without external keys and gives context-aware answers."""
    # 1. Ask who is leading
    resp1 = client.post("/api/recruiter/voice-assist", json={"query": "Who is the top candidate?"})
    assert resp1.status_code == 200
    d1 = resp1.json()
    assert "top" in d1["reply_text"].lower() or "score" in d1["reply_text"].lower()

    # 2. Ask comparison
    resp2 = client.post("/api/recruiter/voice-assist", json={"query": "Compare Sarah and Alex"})
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert "sarah" in d2["reply_text"].lower() and "alex" in d2["reply_text"].lower()

    # 3. Ask skill inquiry
    resp3 = client.post("/api/recruiter/voice-assist", json={"query": "Who has PyTorch experience?"})
    assert resp3.status_code == 200
    d3 = resp3.json()
    assert "pytorch" in d3["reply_text"].lower()

    # 4. Action command
    resp4 = client.post("/api/recruiter/voice-assist", json={"query": "Shortlist Alex Vance"})
    assert resp4.status_code == 200
    d4 = resp4.json()
    assert d4["action_taken"] in ["SHORTLIST", "SHORTLISTED"]
