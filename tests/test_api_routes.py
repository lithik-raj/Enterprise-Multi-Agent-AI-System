"""
Phase 3 — API route integration tests.
Run with:   pytest tests/test_api_routes.py -v

All tests use httpx ASGITransport (no live server required).
File upload tests use in-memory bytes — no real files needed.
"""

import io
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


# ── Health (regression) ───────────────────────────────────────────────────────

async def test_health_still_ok(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200


# ── POST /api/chat ────────────────────────────────────────────────────────────

async def test_chat_accepts_valid_request(client):
    resp = await client.post("/api/chat", json={"message": "Analyse my resume."})
    assert resp.status_code == 202
    body = resp.json()
    assert "task_id" in body
    assert body["status"] == "pending"


async def test_chat_returns_session_id(client):
    resp = await client.post("/api/chat", json={"message": "Analyse my skills."})
    body = resp.json()
    assert "session_id" in body
    assert len(body["session_id"]) > 0


async def test_chat_echos_provided_session_id(client):
    resp = await client.post(
        "/api/chat",
        json={"message": "Test", "session_id": "my-session-99"},
    )
    assert resp.json()["session_id"] == "my-session-99"


async def test_chat_rejects_blank_message(client):
    resp = await client.post("/api/chat", json={"message": "   "})
    assert resp.status_code == 422


async def test_chat_rejects_missing_message(client):
    resp = await client.post("/api/chat", json={})
    assert resp.status_code == 422


# ── POST /api/analyze ─────────────────────────────────────────────────────────

async def test_analyze_accepts_valid_request(client):
    resp = await client.post("/api/analyze", json={"task": "Skill gap analysis please."})
    assert resp.status_code == 202
    assert "task_id" in resp.json()


async def test_analyze_rejects_short_task(client):
    resp = await client.post("/api/analyze", json={"task": "hi"})
    assert resp.status_code == 422


# ── GET /api/task/{task_id} ───────────────────────────────────────────────────

async def test_get_task_returns_task_result(client):
    resp = await client.get("/api/task/some-valid-task-id-123")
    assert resp.status_code == 200
    body = resp.json()
    assert body["task_id"] == "some-valid-task-id-123"
    assert "status" in body
    assert "agent_steps" in body


async def test_get_task_rejects_short_id(client):
    resp = await client.get("/api/task/ab")
    assert resp.status_code == 400


# ── POST /api/upload ──────────────────────────────────────────────────────────

async def test_upload_valid_txt(client):
    content = b"This is my resume content."
    resp = await client.post(
        "/api/upload",
        files={"file": ("resume.txt", io.BytesIO(content), "text/plain")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "document_id" in body
    assert body["file_type"] == "txt"
    assert body["size_bytes"] == len(content)


async def test_upload_valid_pdf(client):
    content = b"%PDF-1.4 fake pdf content for testing"
    resp = await client.post(
        "/api/upload",
        files={"file": ("job_description.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["file_type"] == "pdf"


async def test_upload_rejects_unsupported_type(client):
    resp = await client.post(
        "/api/upload",
        files={"file": ("script.py", io.BytesIO(b"print('hello')"), "text/plain")},
    )
    assert resp.status_code == 415


async def test_upload_rejects_empty_file(client):
    resp = await client.post(
        "/api/upload",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert resp.status_code == 400


# ── POST /api/approve ─────────────────────────────────────────────────────────

async def test_approve_action_approve(client):
    resp = await client.post(
        "/api/approve",
        json={"task_id": "task-abc", "action": "approve"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "approve"
    assert "APPROVED" in body["message"]


async def test_approve_action_reject(client):
    resp = await client.post(
        "/api/approve",
        json={"task_id": "task-abc", "action": "reject", "reason": "Wrong role."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "reject"
    assert "REJECTED" in body["message"]


async def test_approve_rejects_invalid_action(client):
    resp = await client.post(
        "/api/approve",
        json={"task_id": "task-abc", "action": "maybe"},
    )
    assert resp.status_code == 422
