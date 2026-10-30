"""
tests/test_recruiter_app.py

Phase 3 Test Suite: Recruiter Dashboard, Batch Screening Pipeline,
Human-in-the-Loop Decisions (approve, reject, hold), Communicator Agent Email Drafts,
and Traceable Audit Logging.
"""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.database.base import SessionLocal, init_db
from app.database.models import DecisionRecord, AuditLogRecord, MatchRecord
from app.core.auth import AuthUser, UserRole, create_access_token


@pytest.fixture(autouse=True)
def ensure_db():
    init_db()


@pytest.fixture
def recruiter_client():
    tenant_id = f"tenant_{uuid.uuid4().hex[:8]}"
    user = AuthUser(
        id=f"user_{uuid.uuid4().hex[:6]}",
        tenant_id=tenant_id,
        email="recruiter@enterprise.com",
        role=UserRole.RECRUITER,
    )
    token = create_access_token(user)
    return {"token": token, "tenant_id": tenant_id, "user": user}


@pytest.mark.asyncio
async def test_recruiter_end_to_end_workflow(recruiter_client):
    """
    Complete end-to-end recruiter workflow:
    1. Create Job Opening
    2. Batch screen 3 candidate resumes
    3. Retrieve ranked shortlist
    4. Approve top candidate with mandatory human reasoning
    5. Draft interview invitation email (auto-send permanently blocked)
    6. Verify audit log captures trace IDs
    """
    token = recruiter_client["token"]
    tenant_id = recruiter_client["tenant_id"]
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Job
        job_resp = await client.post(
            "/api/recruiter/jobs",
            headers=headers,
            json={
                "title": "Senior AI Systems Engineer",
                "description": (
                    "Seeking a Senior AI Engineer with 5+ years of experience.\n"
                    "Requirements: Python, FastAPI, LangGraph, Docker, PostgreSQL.\n"
                    "Nice to have: PyTorch, Kubernetes."
                ),
            },
        )
        assert job_resp.status_code == 201
        job_data = job_resp.json()
        job_id = job_data["id"]
        assert job_data["title"] == "Senior AI Systems Engineer"

        # 2. Batch Screen 3 Resumes
        resumes = [
            {
                "filename": "top_candidate.txt",
                "content_text": (
                    "Alice Sterling\nSenior AI Architect\nalice@topai.com\n"
                    "Summary: 6.0 years of experience building Python and FastAPI multi-agent systems with LangGraph.\n"
                    "Skills: Python, FastAPI, LangGraph, Docker, PostgreSQL, PyTorch, Kubernetes\n"
                    "Experience: Staff AI Architect (2020 - 2026)\n"
                ),
            },
            {
                "filename": "mid_candidate.txt",
                "content_text": (
                    "Bob Miller\nSoftware Engineer\nbob@dev.io\n"
                    "Summary: 3.5 years of experience in Python web development.\n"
                    "Skills: Python, FastAPI, PostgreSQL, Docker\n"
                    "Experience: Backend Developer (2022 - 2026)\n"
                ),
            },
            {
                "filename": "junior_candidate.txt",
                "content_text": (
                    "Charlie Green\nJunior Web Intern\ncharlie@junior.org\n"
                    "Summary: 1.0 years of experience in HTML and basic styling.\n"
                    "Skills: HTML, CSS, JavaScript\n"
                    "Experience: Intern (2025 - 2026)\n"
                ),
            },
        ]

        screen_resp = await client.post(
            f"/api/recruiter/jobs/{job_id}/screen",
            headers=headers,
            json={"resumes": resumes},
        )
        assert screen_resp.status_code == 200
        screen_data = screen_resp.json()
        assert screen_data["candidates_screened"] == 3
        assert "trace_id" in screen_data

        # 3. Retrieve Ranked Shortlist
        shortlist_resp = await client.get(
            f"/api/recruiter/jobs/{job_id}/shortlist",
            headers=headers,
        )
        assert shortlist_resp.status_code == 200
        shortlist_data = shortlist_resp.json()
        items = shortlist_data["shortlist"]
        assert len(items) == 3

        # Verify descending order of scores
        scores = [item["overall_score"] for item in items]
        assert scores == sorted(scores, reverse=True)

        top_match = items[0]
        assert top_match["overall_score"] >= 80.0
        assert top_match["critic_status"] == "pass"
        top_match_id = top_match["match_id"]

        # 4. Mandatory Human Decision (Approve)
        decide_resp = await client.post(
            f"/api/recruiter/matches/{top_match_id}/decide",
            headers=headers,
            json={
                "decision": "approve",
                "reason": "Outstanding expertise in LangGraph and FastAPI with 6 years experience.",
            },
        )
        assert decide_resp.status_code == 200
        decide_data = decide_resp.json()
        assert decide_data["decision"] == "approve"

        # 5. Communicator Agent Email Draft
        draft_resp = await client.post(
            f"/api/recruiter/matches/{top_match_id}/draft-email",
            headers=headers,
        )
        assert draft_resp.status_code == 200
        draft_data = draft_resp.json()
        assert draft_data["action_type"] == "interview_invitation"
        assert draft_data["auto_send_blocked"] is True
        assert draft_data["requires_human_approval"] is True
        assert "Interview Invitation" in draft_data["subject"]

        # 6. Reject Underqualified Candidate with Human Reasoning
        junior_match = items[-1]
        junior_match_id = junior_match["match_id"]
        reject_resp = await client.post(
            f"/api/recruiter/matches/{junior_match_id}/decide",
            headers=headers,
            json={
                "decision": "reject",
                "reason": "Missing required Python and LangGraph experience.",
            },
        )
        assert reject_resp.status_code == 200

        reject_draft_resp = await client.post(
            f"/api/recruiter/matches/{junior_match_id}/draft-email",
            headers=headers,
        )
        assert reject_draft_resp.status_code == 200
        assert reject_draft_resp.json()["action_type"] == "polite_rejection"

        # 7. Verify Database Audit Trail Persistence
        with SessionLocal() as session:
            audits = session.execute(
                select(AuditLogRecord).where(AuditLogRecord.tenant_id == tenant_id)
            ).scalars().all()
            assert len(audits) >= 4  # job_created, screening_run, 2 decisions, 2 drafts
            actions = [a.action for a in audits]
            assert "job_created" in actions
            assert "screening_run_completed" in actions
            assert "candidate_decision_approve" in actions
            assert "candidate_decision_reject" in actions
