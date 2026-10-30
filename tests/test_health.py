"""
Phase 1 — Health endpoint tests.
Run with:   pytest tests/test_health.py -v
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.mark.anyio
async def test_health_returns_200(client):
    """GET /api/health must return HTTP 200."""
    response = await client.get("/api/health")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_health_response_body(client):
    """Response must contain status=ok and version fields."""
    response = await client.get("/api/health")
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "app" in body


@pytest.mark.anyio
async def test_health_content_type(client):
    """Response must be JSON."""
    response = await client.get("/api/health")
    assert "application/json" in response.headers["content-type"]
