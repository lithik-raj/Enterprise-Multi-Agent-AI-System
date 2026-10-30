"""
Phase 12 & 13 Integration Tests.

Validates:
- Human-in-the-Loop approval listing and resolution endpoints
- Frontend HTML, CSS, and JS static file delivery
- Tasks listing and platform statistics endpoints
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


# ── Phase 13: Frontend Static Delivery Tests ─────────────────────────────────

async def test_frontend_index_html_served(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "Enterprise Multi-Agent AI Intelligence Platform" in resp.text
    assert "NexusAgent AI" in resp.text


async def test_frontend_styles_css_served(client):
    resp = await client.get("/css/styles.css")
    assert resp.status_code == 200
    assert "--bg-primary" in resp.text
    assert "--gradient-primary" in resp.text


async def test_frontend_app_js_served(client):
    resp = await client.get("/js/app.js")
    assert resp.status_code == 200
    assert "loadDashboardData" in resp.text
    assert "pollTaskWorkflow" in resp.text


async def test_frontend_api_js_served(client):
    resp = await client.get("/js/api.js")
    assert resp.status_code == 200
    assert "getStats" in resp.text
    assert "submitChat" in resp.text


async def test_frontend_three_js_served(client):
    resp = await client.get("/js/three.min.js")
    assert resp.status_code == 200
    assert len(resp.content) > 100000


async def test_frontend_quantum_universe_served(client):
    resp = await client.get("/js/quantum-universe.js")
    assert resp.status_code == 200
    assert "initQuantumUniverse" in resp.text
    assert "quantum-universe-canvas" in resp.text


# ── Phase 12: Human-in-the-Loop & Governance Tests ───────────────────────────

async def test_approvals_list_pending(client):
    resp = await client.get("/api/approvals")
    assert resp.status_code == 200
    approvals = resp.json()
    assert isinstance(approvals, list)


async def test_approvals_resolve_flow(client):
    # Fetch pending approvals
    resp = await client.get("/api/approvals")
    approvals = resp.json()
    if approvals:
        target_id = approvals[0]["task_id"]
        # Approve target action
        approve_resp = await client.post(
            "/api/approve",
            json={"task_id": target_id, "action": "approve"},
        )
        assert approve_resp.status_code == 200
        assert "APPROVED" in approve_resp.json()["message"]


async def test_approvals_reject_flow(client):
    resp = await client.post(
        "/api/approve",
        json={
            "task_id": "task-test-reject-001",
            "action": "reject",
            "reason": "Not approved by safety officer",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "reject"
    assert "REJECTED" in body["message"]


# ── Platform Stats & Task Tracking ───────────────────────────────────────────

async def test_stats_endpoint(client):
    resp = await client.get("/api/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert "total_tasks" in stats
    assert "agents_active" in stats
    assert stats["agents_active"] == 7
    assert stats["system_health"] == "operational"


async def test_tasks_list_endpoint(client):
    resp = await client.get("/api/tasks")
    assert resp.status_code == 200
    tasks = resp.json()
    assert isinstance(tasks, list)
    assert len(tasks) > 0


async def test_documents_list_endpoint(client):
    resp = await client.get("/api/documents")
    assert resp.status_code == 200
    docs = resp.json()
    assert isinstance(docs, list)
