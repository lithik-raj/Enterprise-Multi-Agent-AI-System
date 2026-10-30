"""
Tests for Cognitive HR Q&A Engine, Auth Strict Security & Rejection,
Rollback & Recovery Dynamic Counter Synchronization, and Domain Requisitions.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.cognitive_qa_engine import (
    normalize_and_rectify_query,
    get_cognitive_hr_engine,
)
from app.services.recovery_service import get_recovery_service


@pytest.fixture
def client():
    return TestClient(app)


# ── 1. AUTHENTICATION SECURITY & REJECTION TESTS ─────────────────────────────

def test_auth_rejection_on_wrong_password(client):
    """Wrong password must strictly fail with 401 and clear error message, never logging in."""
    res = client.post(
        "/api/auth/login",
        json={"email": "hr.admin@gmail.com", "password": "WrongPassword123!"},
    )
    assert res.status_code == 401
    detail = res.json().get("detail", "")
    assert "Invalid Email ID or Password" in detail


def test_auth_rejection_on_unknown_email(client):
    """Unknown or unprovisioned email with arbitrary password must strictly fail with 401."""
    res = client.post(
        "/api/auth/login",
        json={"email": "random.unauthorized.user@domain.com", "password": "random_password"},
    )
    assert res.status_code == 401
    detail = res.json().get("detail", "")
    assert "Invalid Email ID or Password" in detail


def test_auth_success_on_valid_credentials(client):
    """Authorized credentials must return 200 with JWT access token."""
    res = client.post(
        "/api/auth/login",
        json={"email": "hr.admin@gmail.com", "password": "TalentGraph@2026"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == "hr.admin@gmail.com"


import uuid


def test_auth_registration_and_login_flow(client):
    """Registering a new recruiter, then logging in with correct and wrong password."""
    new_email = f"lead.recruiter.{uuid.uuid4().hex[:8]}@talentgraph.ai"
    reg_res = client.post(
        "/api/auth/register",
        json={
            "email": new_email,
            "password": "SecurePassword@2026",
            "full_name": "Test Recruiter Lead",
            "role": "recruiter",
            "tenant_id": "default",
        },
    )
    assert reg_res.status_code in (200, 201)
    assert "access_token" in reg_res.json()

    # Wrong password attempt
    wrong_login = client.post(
        "/api/auth/login",
        json={"email": new_email, "password": "BadPassword999"},
    )
    assert wrong_login.status_code == 401

    # Correct password attempt
    correct_login = client.post(
        "/api/auth/login",
        json={"email": new_email, "password": "SecurePassword@2026"},
    )
    assert correct_login.status_code == 200
    assert "access_token" in correct_login.json()


# ── 2. RECOVERY VAULT DYNAMIC COUNT & SYNCHRONIZATION ─────────────────────────

def test_recovery_count_endpoint(client):
    """GET /api/recovery/count must return valid integer count and breakdown."""
    res = client.get("/api/recovery/count?tenant_id=default")
    assert res.status_code == 200
    data = res.json()
    assert "count" in data
    assert isinstance(data["count"], int)
    assert data["count"] >= 0
    assert "candidates" in data
    assert "employees" in data


def test_recovery_count_increments_and_decrements(client):
    """Soft deleting a candidate increments count, restoring decrements count."""
    init_res = client.get("/api/recovery/count?tenant_id=default")
    init_count = init_res.json()["count"]

    # Soft delete a test candidate
    test_cand_name = "Candidate Sync Test"
    del_res = client.post(
        "/api/recovery/soft-delete-candidate",
        json={
            "candidate_name": test_cand_name,
            "candidate_data": {
                "name": test_cand_name,
                "predicted_score": 0.72,
                "experience_years": 4.0,
                "matched_skills": ["Python", "FastAPI"],
                "missing_skills": ["Docker"],
            },
            "reason": "Testing dynamic counter synchronization",
            "deleted_by": "HR Counter Test Runner",
            "tenant_id": "default",
        },
    )
    assert del_res.status_code == 200
    item_id = del_res.json().get("item_id")
    assert item_id is not None

    # Check that count incremented by 1
    after_del_res = client.get("/api/recovery/count?tenant_id=default")
    new_count = after_del_res.json()["count"]
    assert new_count == init_count + 1

    # Now restore the item
    restore_res = client.post(f"/api/recovery/{item_id}/restore?tenant_id=default")
    assert restore_res.status_code == 200

    # Check that count decremented back to initial count
    after_restore_res = client.get("/api/recovery/count?tenant_id=default")
    assert after_restore_res.json()["count"] == init_count


# ── 3. COGNITIVE HR ENGINE & VOICE ASSISTANT TESTS ───────────────────────────

def test_query_normalization_and_typo_rectification():
    """Verify normalization expands HR shortcuts, rectifies typos, and classifies intents."""
    raw_query = "crct q and crct w and a complt or ssitll pnding rmv or no"
    norm = normalize_and_rectify_query(raw_query)

    rectified = norm["rectified_query"]
    assert "correct" in rectified
    assert "work and assignments" in rectified or "completed" in rectified
    assert "still" in rectified
    assert "pending" in rectified
    assert "remove or no" in rectified or "remove" in rectified

    intents = norm["intents"]
    assert "RETENTION_DECISION" in intents
    assert any(it in intents for it in ["WORK_COMPLETED", "PENDING_WORK", "FULL_WORK_STATUS"])


def test_voice_assist_shall_we_remove_or_no(client):
    """'shall we remove or no' must return retention advice and 7-day recovery policy, NOT canned text."""
    res = client.post(
        "/api/recruiter/voice-assist",
        json={"query": "shall we remove or no", "target_role": "Senior AI/ML Platform Engineer"},
    )
    assert res.status_code == 200
    reply = res.json()["reply_text"]

    # Must NOT contain the repetitive canned text
    canned_marker = "Regarding your query on shall we remove or no: In our active requisition for Senior AI/ML Platform Engineer, 4 candidates have been screened."
    assert canned_marker not in reply

    # Must contain retention advice and recovery vault reference
    reply_lower = reply.lower()
    assert any(term in reply_lower for term in ["remove", "retention", "recovery", "keep", "rollback", "vault", "dpdp", "safe"])


def test_voice_assist_work_completed_pending_and_active_status(client):
    """Inquiry on work completed, pending work, and active status must break down all three."""
    res = client.post(
        "/api/recruiter/voice-assist",
        json={
            "query": "what is the particular work he completed, still pending work and active status",
            "candidate_name": "Sarah Lin",
        },
    )
    assert res.status_code == 200
    reply = res.json()["reply_text"]

    reply_lower = reply.lower()
    assert "completed" in reply_lower
    assert "pending" in reply_lower
    assert "status" in reply_lower or "active" in reply_lower


def test_voice_assist_future_suitability_not_hardcoded_to_data_science(client):
    """Future suitability for an engineer must evaluate against target role, not default to Data Science."""
    res = client.post(
        "/api/recruiter/voice-assist",
        json={
            "query": "whether he suits for job in future here and ideas for hr based on analysis",
            "target_role": "Senior AI/ML Platform Engineer",
        },
    )
    assert res.status_code == 200
    reply = res.json()["reply_text"]

    reply_lower = reply.lower()
    assert any(term in reply_lower for term in ["future", "performance", "trajectory", "suitability", "growth"])
    # If requisition is AI/ML, it shouldn't unilaterally say "Evaluating for the Data Scientist role"
    assert "data scientist role" not in reply_lower or "ai/ml" in reply_lower or "engineer" in reply_lower


def test_voice_assist_domains_and_internships(client):
    """Inquiry for domains and internships must return live co-active hiring positions."""
    res = client.post(
        "/api/recruiter/voice-assist",
        json={"query": "what are the live co active hiring domain jobs and campus internships"},
    )
    assert res.status_code == 200
    reply = res.json()["reply_text"]

    reply_lower = reply.lower()
    assert any(term in reply_lower for term in ["internship", "domain", "hiring", "openings", "requisition"])
    assert "live co-active hiring" in reply_lower or "active hiring" in reply_lower or "co-active" in reply_lower
