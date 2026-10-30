"""
tests/test_expand_and_deploy.py

Phase 5 Test Suite: Expand & Deploy
- Bidirectional ATS integrations (Greenhouse, Lever, Workday)
- Internal mobility suggestions and upskilling pathways
- Production deployment verification and health verification
"""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database.base import init_db
from app.core.auth import AuthUser, UserRole, create_access_token
from app.services.ats_integrations import ATSConnector
from app.agents.internal_mobility_agent import InternalEmployee, InternalMobilityAgent
from app.agents.job_analyzer_agent import JobAnalyzerAgent


@pytest.fixture(autouse=True)
def ensure_db():
    init_db()


@pytest.fixture
def recruiter_client():
    tenant_id = f"tenant_{uuid.uuid4().hex[:8]}"
    user = AuthUser(
        id=f"recruiter_{uuid.uuid4().hex[:6]}",
        tenant_id=tenant_id,
        email="talent.lead@acme.org",
        role=UserRole.RECRUITER,
    )
    token = create_access_token(user)
    return {"token": token, "tenant_id": tenant_id, "user": user}


def test_ats_connector_sync_and_export():
    """Verify bidirectional sync with external ATS platforms (Greenhouse, Lever, Workday)."""
    for provider in ["greenhouse", "lever", "workday"]:
        connector = ATSConnector(provider=provider)

        # 1. Import candidates from ATS
        candidates = connector.import_candidates(job_id="ext_job_42", count=2)
        assert len(candidates) == 2
        assert candidates[0].ats_provider == provider
        assert "@" in candidates[0].email

        # 2. Export recruiter hire decision back to ATS
        res = connector.export_decision(
            candidate_ats_id=candidates[0].ats_id,
            decision="approve",
            reason="Exceptional alignment with LLM multi-agent engineering.",
        )
        assert res.success is True
        assert res.ats_provider == provider
        assert "Advanced to Hiring Manager Screen" in res.status_message


def test_internal_mobility_agent_matching():
    """Verify internal employee talent matching and upskilling pathways."""
    analyzer = JobAnalyzerAgent()
    job = analyzer.analyze(
        "Lead AI Platform Architect",
        "Lead role requiring 6+ years experience. Must-have: Python, FastAPI, Docker, Kubernetes, LangGraph.",
    )

    employees = [
        InternalEmployee(
            employee_id="emp_001",
            name="Vikram Rao",
            current_role="Senior Software Engineer",
            department="Core Infrastructure",
            tenure_years=5.0,
            skills=["Python", "FastAPI", "Docker", "Kubernetes", "LangGraph"],
            performance_rating=4.8,
        ),
        InternalEmployee(
            employee_id="emp_002",
            name="Chloe Dubois",
            current_role="Backend Developer",
            department="Growth",
            tenure_years=2.0,
            skills=["Python", "FastAPI", "Docker"],
            performance_rating=4.2,
        ),
    ]

    agent = InternalMobilityAgent()
    matches = agent.evaluate_internal_talent(employees, job)

    assert len(matches) == 2
    top = matches[0]
    assert top.employee_name == "Vikram Rao"
    assert top.readiness_level == "Immediate Transition"
    assert "Kubernetes" in top.matched_competencies

    runner_up = matches[1]
    assert runner_up.employee_name == "Chloe Dubois"
    assert "Langgraph" in [s.title() for s in runner_up.suggested_upskilling] or "Kubernetes" in [s.title() for s in runner_up.suggested_upskilling]


@pytest.mark.asyncio
async def test_ats_api_endpoints(recruiter_client):
    """Test API integration endpoints for ATS sync and mobility."""
    token = recruiter_client["token"]
    tenant_id = recruiter_client["tenant_id"]
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test ATS Sync
        sync_resp = await client.post(
            "/api/expansion/ats/sync-candidates",
            headers=headers,
            json={"provider": "lever", "job_id": "job_dev_100", "candidates_count": 2},
        )
        assert sync_resp.status_code == 200
        data = sync_resp.json()
        assert data["provider"] == "lever"
        assert len(data["candidates"]) == 2

        # Test ATS Decision Export
        export_resp = await client.post(
            "/api/expansion/ats/export-decision",
            headers=headers,
            json={
                "provider": "workday",
                "candidate_ats_id": "workday_cand_101",
                "decision": "approve",
                "reason": "Top performer in technical evaluation.",
            },
        )
        assert export_resp.status_code == 200
        assert export_resp.json()["success"] is True


@pytest.mark.asyncio
async def test_deployment_health_and_verification():
    """Verify platform health and deployment readiness."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health_resp = await client.get("/api/health")
        assert health_resp.status_code == 200
        h_data = health_resp.json()
        assert h_data["status"] == "ok"
        assert h_data["guardrails"] == "active"
        assert h_data["monitoring"] == "active"
