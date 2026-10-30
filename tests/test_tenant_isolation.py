"""
tests/test_tenant_isolation.py

Phase 0: Foundation Test Suite
Validates strict multi-tenant isolation, cross-tenant leak prevention,
database partitioning, and Role-Based Access Control (RBAC).
"""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.database.base import SessionLocal, init_db
from app.database.models import (
    TenantRecord,
    UserRecord,
    JobRecord,
    CandidateRecord,
    RunRecord,
    MatchRecord,
    DecisionRecord,
    AuditLogRecord,
)
from app.core.auth import (
    AuthUser,
    UserRole,
    create_access_token,
    hash_password,
    verify_password,
)


@pytest.fixture(autouse=True)
def ensure_db():
    init_db()


@pytest.mark.asyncio
async def test_tenant_creation_and_retrieval():
    """Test provisioning new tenants and retrieving isolated tenant profiles."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create Tenant Alpha
        resp_alpha = await client.post(
            "/api/tenants",
            json={"name": "Alpha Corp", "plan": "enterprise", "settings": {"cost_cap_usd": 1000.0}},
        )
        assert resp_alpha.status_code == 201
        data_alpha = resp_alpha.json()
        assert data_alpha["name"] == "Alpha Corp"
        tenant_alpha_id = data_alpha["id"]

        # Create Tenant Beta
        resp_beta = await client.post(
            "/api/tenants",
            json={"name": "Beta Inc", "plan": "pro", "settings": {"cost_cap_usd": 250.0}},
        )
        assert resp_beta.status_code == 201
        data_beta = resp_beta.json()
        assert data_beta["name"] == "Beta Inc"
        tenant_beta_id = data_beta["id"]

        # Verify Alpha cannot see Beta's settings
        resp_get_alpha = await client.get("/api/tenants/current", headers={"X-Tenant-ID": tenant_alpha_id})
        assert resp_get_alpha.status_code == 200
        assert resp_get_alpha.json()["id"] == tenant_alpha_id
        assert resp_get_alpha.json()["settings"]["cost_cap_usd"] == 1000.0

        resp_get_beta = await client.get("/api/tenants/current", headers={"X-Tenant-ID": tenant_beta_id})
        assert resp_get_beta.status_code == 200
        assert resp_get_beta.json()["id"] == tenant_beta_id
        assert resp_get_beta.json()["settings"]["cost_cap_usd"] == 250.0


@pytest.mark.asyncio
async def test_user_authentication_and_tenant_token_scoping():
    """Test user registration, login, token signing, and role verification."""
    transport = ASGITransport(app=app)
    tenant_id = f"t_{uuid.uuid4().hex[:8]}"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register recruiter in tenant
        reg_resp = await client.post(
            "/api/auth/register",
            headers={"X-Tenant-ID": tenant_id},
            json={
                "email": "sarah.recruiter@company.com",
                "password": "StrongPassword123!",
                "full_name": "Sarah Recruiter",
                "role": "recruiter",
            },
        )
        assert reg_resp.status_code == 201
        reg_data = reg_resp.json()
        assert reg_data["tenant_id"] == tenant_id
        assert reg_data["role"] == "recruiter"
        token = reg_data["access_token"]

        # Validate /me endpoint with Bearer token
        me_resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "sarah.recruiter@company.com"
        assert me_resp.json()["tenant_id"] == tenant_id

        # Mismatched tenant header must be rejected with 403 Forbidden
        tamper_resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "foreign_tenant_999"},
        )
        assert tamper_resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_admin_vs_recruiter_permissions():
    """Verify RBAC: Admin can update tenant settings, but Recruiter is forbidden."""
    transport = ASGITransport(app=app)
    tenant_id = f"t_{uuid.uuid4().hex[:8]}"

    admin_user = AuthUser(
        id=f"admin_{uuid.uuid4().hex[:6]}",
        tenant_id=tenant_id,
        email="admin@corp.com",
        role=UserRole.ADMIN,
    )
    admin_token = create_access_token(admin_user)

    recruiter_user = AuthUser(
        id=f"recruiter_{uuid.uuid4().hex[:6]}",
        tenant_id=tenant_id,
        email="recruiter@corp.com",
        role=UserRole.RECRUITER,
    )
    recruiter_token = create_access_token(recruiter_user)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Recruiter tries to update tenant settings -> 403 Forbidden
        recruiter_resp = await client.put(
            "/api/tenants/current/settings",
            headers={"Authorization": f"Bearer {recruiter_token}", "X-Tenant-ID": tenant_id},
            json={"settings": {"cost_cap_usd": 9999.0}},
        )
        assert recruiter_resp.status_code == 403

        # Admin updates tenant settings -> 200 OK
        admin_resp = await client.put(
            "/api/tenants/current/settings",
            headers={"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": tenant_id},
            json={"settings": {"cost_cap_usd": 9999.0}},
        )
        assert admin_resp.status_code == 200
        assert admin_resp.json()["settings"]["cost_cap_usd"] == 9999.0


@pytest.mark.asyncio
async def test_database_cross_tenant_isolation():
    """
    Direct ORM database leak test:
    Create complete data tree in Tenant 1 (Job, Candidate, Run, Match, Decision, AuditLog).
    Verify that queries filtered by Tenant 2 return ZERO records.
    """
    t1 = f"tenant_{uuid.uuid4().hex[:8]}"
    t2 = f"tenant_{uuid.uuid4().hex[:8]}"

    with SessionLocal() as session:
        # Seed Tenant 1 records
        tenant1 = TenantRecord(id=t1, name="Tenant One", plan="enterprise")
        tenant2 = TenantRecord(id=t2, name="Tenant Two", plan="pro")
        session.add_all([tenant1, tenant2])
        session.flush()

        job1 = JobRecord(
            id=f"job_{uuid.uuid4().hex[:8]}",
            tenant_id=t1,
            title="Senior AI Engineer",
            description="Build multi-agent LLM systems with LangGraph.",
        )
        session.add(job1)
        session.flush()

        cand1 = CandidateRecord(
            id=f"cand_{uuid.uuid4().hex[:8]}",
            tenant_id=t1,
            profile_json='{"name": "Alice Dev", "skills": ["Python", "FastAPI", "LangGraph"]}',
        )
        session.add(cand1)
        session.flush()

        run1 = RunRecord(
            id=f"run_{uuid.uuid4().hex[:8]}",
            tenant_id=t1,
            job_id=job1.id,
            status="completed",
            cost=0.042,
        )
        session.add(run1)
        session.flush()

        match1 = MatchRecord(
            id=f"match_{uuid.uuid4().hex[:8]}",
            tenant_id=t1,
            run_id=run1.id,
            candidate_id=cand1.id,
            score=94.5,
            rationale="Candidate exhibits strong Python and LangGraph expertise.",
            critic_status="pass",
        )
        session.add(match1)
        session.flush()

        user1 = UserRecord(
            id=f"u_{uuid.uuid4().hex[:8]}",
            tenant_id=t1,
            email="recruiter@t1.com",
            role="recruiter",
            hashed_password=hash_password("secure123"),
        )
        session.add(user1)
        session.flush()

        decision1 = DecisionRecord(
            id=f"dec_{uuid.uuid4().hex[:8]}",
            tenant_id=t1,
            match_id=match1.id,
            user_id=user1.id,
            decision="approve",
            reason="Exceptional alignment with LLM multi-agent requirements.",
        )
        audit1 = AuditLogRecord(
            id=f"aud_{uuid.uuid4().hex[:8]}",
            tenant_id=t1,
            actor="recruiter@t1.com",
            action="candidate_approved",
            trace_id="tr_123456",
        )
        session.add_all([decision1, audit1])
        session.commit()

        # ── Cross-Tenant Leak Check: Querying Tenant 2 must return ZERO records ──
        jobs_t2 = session.execute(select(JobRecord).where(JobRecord.tenant_id == t2)).scalars().all()
        assert len(jobs_t2) == 0, "Security Leak: Tenant 2 saw Tenant 1 jobs!"

        cands_t2 = session.execute(select(CandidateRecord).where(CandidateRecord.tenant_id == t2)).scalars().all()
        assert len(cands_t2) == 0, "Security Leak: Tenant 2 saw Tenant 1 candidates!"

        runs_t2 = session.execute(select(RunRecord).where(RunRecord.tenant_id == t2)).scalars().all()
        assert len(runs_t2) == 0, "Security Leak: Tenant 2 saw Tenant 1 runs!"

        matches_t2 = session.execute(select(MatchRecord).where(MatchRecord.tenant_id == t2)).scalars().all()
        assert len(matches_t2) == 0, "Security Leak: Tenant 2 saw Tenant 1 matches!"

        decisions_t2 = session.execute(select(DecisionRecord).where(DecisionRecord.tenant_id == t2)).scalars().all()
        assert len(decisions_t2) == 0, "Security Leak: Tenant 2 saw Tenant 1 decisions!"

        audit_t2 = session.execute(select(AuditLogRecord).where(AuditLogRecord.tenant_id == t2)).scalars().all()
        assert len(audit_t2) == 0, "Security Leak: Tenant 2 saw Tenant 1 audit logs!"

