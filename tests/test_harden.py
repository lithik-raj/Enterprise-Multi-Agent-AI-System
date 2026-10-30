"""
tests/test_harden.py

Phase 4 Test Suite: System Hardening
- Tenant cost caps and budget overrun prevention
- Distributed telemetry tracing with W3C-compatible IDs
- DPDP Act & GDPR compliance (consent, DSAR export, right-to-erasure)
- Configurable retention policy enforcement
- High-throughput load benchmark (500 resumes < 15 minutes target)
"""

import time
import uuid
from datetime import datetime, timedelta
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.database.base import SessionLocal, init_db
from app.database.models import CandidateRecord, TenantRecord, RunRecord, AuditLogRecord
from app.core.auth import AuthUser, UserRole, create_access_token
from app.core.telemetry import TraceSpan, get_current_trace_id
from app.services.cost_service import CostService, CostCapExceededError
from app.agents.parser_agent import ParserAgent
from app.agents.extractor_agent import ExtractorAgent
from app.agents.bias_masker_agent import BiasMaskerAgent
from app.agents.matcher_agent import MatcherAgent
from app.agents.job_analyzer_agent import JobAnalyzerAgent


@pytest.fixture(autouse=True)
def ensure_db():
    init_db()


@pytest.fixture
def admin_client():
    tenant_id = f"tenant_{uuid.uuid4().hex[:8]}"
    user = AuthUser(
        id=f"admin_{uuid.uuid4().hex[:6]}",
        tenant_id=tenant_id,
        email="compliance.officer@corp.com",
        role=UserRole.ADMIN,
    )
    token = create_access_token(user)
    return {"token": token, "tenant_id": tenant_id, "user": user}


def test_telemetry_span_measurement():
    """Verify TraceSpan captures trace IDs, attributes, and measures execution duration."""
    with TraceSpan("agent_screening_span", attributes={"agent": "MatcherAgent"}) as span:
        time.sleep(0.01)  # 10ms work simulation

    assert span.span_id.startswith("sp_")
    assert span.trace_id.startswith("tr_")
    assert span.duration_ms >= 8.0
    assert span.attributes["agent"] == "MatcherAgent"


def test_tenant_cost_cap_enforcement(admin_client):
    """Verify that tenants cannot exceed their allocated budget cap."""
    tenant_id = admin_client["tenant_id"]
    cost_svc = CostService()

    with SessionLocal() as session:
        # Create tenant with very strict $0.05 cap
        t = TenantRecord(
            id=tenant_id,
            name="Budget Tenant",
            settings_json='{"cost_cap_usd": 0.05}',
        )
        session.add(t)

        # Record existing run of $0.04
        r = RunRecord(
            id=f"run_{uuid.uuid4().hex[:8]}",
            tenant_id=tenant_id,
            job_id="job_1",
            cost=0.04,
            status="completed",
        )
        session.add(r)
        session.commit()

        # Screening 1 resume ($0.005) is permitted (total $0.045 <= $0.05)
        cost_svc.verify_budget_availability(tenant_id, resume_count=1, db=session)

        # Screening 5 resumes ($0.025) exceeds cap (total $0.065 > $0.05) -> raises CostCapExceededError
        with pytest.raises(CostCapExceededError):
            cost_svc.verify_budget_availability(tenant_id, resume_count=5, db=session)


@pytest.mark.asyncio
async def test_dpdp_and_gdpr_privacy_endpoints(admin_client):
    """
    Test compliance lifecycle:
    1. Consent capture
    2. DSAR data export
    3. Right to Erasure permanent deletion
    """
    token = admin_client["token"]
    tenant_id = admin_client["tenant_id"]
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

    cand_id = f"cand_{uuid.uuid4().hex[:12]}"
    with SessionLocal() as session:
        cand = CandidateRecord(
            id=cand_id,
            tenant_id=tenant_id,
            source_file_id="resume.pdf",
            profile_json='{"name": "Ananya Sen", "email": "ananya@example.com", "skills": ["Python", "FastAPI"]}',
        )
        session.add(cand)
        session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Capture Consent
        consent_resp = await client.post(
            "/api/privacy/consent",
            headers=headers,
            json={"candidate_id": cand_id, "consent_purpose": "AI matching for Senior Engineer", "consent_given": True},
        )
        assert consent_resp.status_code == 201
        assert consent_resp.json()["compliance_standard"] == "DPDP Act 2023 & GDPR Art. 6"

        # 2. DSAR Data Export
        export_resp = await client.get(
            f"/api/privacy/candidates/{cand_id}/export",
            headers=headers,
        )
        assert export_resp.status_code == 200
        data = export_resp.json()
        assert data["candidate_id"] == cand_id
        assert data["profile"]["name"] == "Ananya Sen"

        # 3. Right to Erasure (Delete Candidate)
        del_resp = await client.delete(
            f"/api/privacy/candidates/{cand_id}",
            headers=headers,
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "permanently_deleted"

        # Verify candidate no longer exists in DB
        with SessionLocal() as session:
            check = session.execute(
                select(CandidateRecord).where(CandidateRecord.id == cand_id)
            ).scalar_one_or_none()
            assert check is None

            # Verify audit tombstone recorded
            tombstone = session.execute(
                select(AuditLogRecord).where(
                    AuditLogRecord.tenant_id == tenant_id,
                    AuditLogRecord.action == "candidate_data_erased",
                )
            ).scalar_one_or_none()
            assert tombstone is not None


@pytest.mark.asyncio
async def test_retention_policy_cleanup(admin_client):
    """Verify that candidate records older than tenant retention policy are automatically purged."""
    token = admin_client["token"]
    tenant_id = admin_client["tenant_id"]
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

    with SessionLocal() as session:
        # Tenant with 30-day retention
        tenant = TenantRecord(id=tenant_id, name="Retention Corp", settings_json='{"retention_days": 30}')
        session.add(tenant)

        # Expired candidate (created 60 days ago)
        expired_cand = CandidateRecord(
            id=f"cand_expired_{uuid.uuid4().hex[:6]}",
            tenant_id=tenant_id,
            profile_json='{"name": "Old Applicant"}',
            created_at=datetime.utcnow() - timedelta(days=60),
        )
        # Fresh candidate (created today)
        fresh_cand = CandidateRecord(
            id=f"cand_fresh_{uuid.uuid4().hex[:6]}",
            tenant_id=tenant_id,
            profile_json='{"name": "Recent Applicant"}',
            created_at=datetime.utcnow(),
        )
        session.add_all([expired_cand, fresh_cand])
        session.commit()

        expired_id = expired_cand.id
        fresh_id = fresh_cand.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/privacy/retention/cleanup", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["purged_candidates_count"] >= 1

    with SessionLocal() as session:
        # Expired must be deleted
        assert session.execute(select(CandidateRecord).where(CandidateRecord.id == expired_id)).scalar_one_or_none() is None
        # Fresh must still exist
        assert session.execute(select(CandidateRecord).where(CandidateRecord.id == fresh_id)).scalar_one_or_none() is not None


def test_load_throughput_benchmark_500_resumes_target():
    """
    Load test benchmark:
    Validates screening throughput on 25 varied resumes, calculating resumes/second.
    Target: 500 resumes in < 15 minutes (= 900 seconds, requiring >= 0.55 resumes/sec).
    """
    job_analyzer = JobAnalyzerAgent()
    job_reqs = job_analyzer.analyze(
        "Full Stack AI Developer",
        "Seeking engineer with 4+ years experience. Requirements: Python, FastAPI, React, Docker, SQL."
    )

    parser = ParserAgent()
    extractor = ExtractorAgent()
    masker = BiasMaskerAgent()
    matcher = MatcherAgent()

    test_resume_template = (
        "Candidate Sample {i}\n"
        "Software Engineer with 5 years experience.\n"
        "Skills: Python, FastAPI, React, Docker, PostgreSQL, Redis, Git.\n"
        "Experience: Engineer at Tech Corp (2021 - 2026)\n"
    )

    sample_count = 25
    t0 = time.perf_counter()

    for i in range(sample_count):
        raw_text = test_resume_template.format(i=i)
        parsed = parser.parse_text(raw_text)
        profile = extractor.extract(parsed.clean_text)
        masked = masker.mask(profile)
        match = matcher.match(masked, job_reqs)
        assert match.overall_score >= 80.0

    total_time = time.perf_counter() - t0
    resumes_per_second = sample_count / total_time
    extrapolated_500_time_seconds = 500.0 / resumes_per_second
    extrapolated_500_time_minutes = extrapolated_500_time_seconds / 60.0

    print(f"\nThroughput: {resumes_per_second:.2f} resumes/second")
    print(f"500 Resumes Estimated Time: {extrapolated_500_time_minutes:.2f} minutes (Target: < 15.0 minutes)")

    # Assert required quality target from brief: 500 resumes screened in under 15 minutes
    assert extrapolated_500_time_minutes < 15.0, f"Benchmark failed: took {extrapolated_500_time_minutes:.2f} min"
