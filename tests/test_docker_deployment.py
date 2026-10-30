"""
Phase 16 — Docker & Deployment Preparation Tests.

Validates the containerization and production deployment configuration:
1. Dockerfile structure, layer caching, security, and healthcheck specification.
2. .dockerignore exclusion rules to prevent secret/cache leakage into images.
3. docker-compose.yml services, persistence volumes, and health monitoring.
4. FastAPI application entrypoint (run.py) and /api/health endpoint readiness.
"""

from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


# ── 1. Dockerfile Tests ───────────────────────────────────────────────────────

def test_dockerfile_exists_and_valid():
    """Verify Dockerfile exists and contains required production directives."""
    dockerfile_path = WORKSPACE_ROOT / "Dockerfile"
    assert dockerfile_path.exists(), "Dockerfile must exist at repository root"

    content = dockerfile_path.read_text(encoding="utf-8")

    # Base image
    assert "FROM python:3.11-slim" in content, "Base image must be python:3.11-slim"

    # Production environment flags
    assert "PYTHONUNBUFFERED=1" in content, "PYTHONUNBUFFERED must be enabled for streaming logs"
    assert "PYTHONDONTWRITEBYTECODE=1" in content, "PYTHONDONTWRITEBYTECODE must be enabled"

    # Layer caching: requirements copied before application code
    req_index = content.find("COPY requirements.txt")
    code_index = content.find("COPY . .")
    assert req_index != -1, "Dockerfile must copy requirements.txt"
    assert code_index != -1, "Dockerfile must copy application code"
    assert req_index < code_index, "requirements.txt must be copied before code for Docker caching"

    # Port exposure and healthcheck
    assert "EXPOSE 8000" in content, "Port 8000 must be exposed"
    assert "HEALTHCHECK" in content, "HEALTHCHECK directive must be defined"
    assert "/api/health" in content, "Healthcheck must target /api/health"
    assert 'CMD ["python", "run.py"]' in content, "Default CMD must invoke run.py"


# ── 2. .dockerignore Tests ────────────────────────────────────────────────────

def test_dockerignore_exists_and_excludes_secrets():
    """Verify .dockerignore exists and excludes secrets, caches, and unnecessary artifacts."""
    dockerignore_path = WORKSPACE_ROOT / ".dockerignore"
    assert dockerignore_path.exists(), ".dockerignore must exist at repository root"

    content = dockerignore_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

    assert ".env" in lines, ".env must be ignored in docker builds"
    assert "__pycache__/" in lines or "__pycache__" in lines, "Python bytecode cache must be ignored"
    assert ".pytest_cache/" in lines or ".pytest_cache" in lines, "Pytest cache must be ignored"
    assert ".git" in lines or ".git/" in lines, ".git directory must be ignored"


# ── 3. docker-compose.yml Tests ───────────────────────────────────────────────

def test_docker_compose_configuration():
    """Verify docker-compose.yml specifies proper ports, environment, volumes, and health checks."""
    compose_path = WORKSPACE_ROOT / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist"

    content = compose_path.read_text(encoding="utf-8")

    assert "enterprise-ai-platform" in content or "services:" in content
    assert '"8000:8000"' in content or "8000:8000" in content, "Port 8000 must be mapped"
    assert "./data:/app/data" in content, "Data volume must be mounted for persistent storage"
    assert "./uploads:/app/uploads" in content, "Uploads volume must be mounted for persistent files"
    assert "/api/health" in content, "Docker compose must configure healthcheck using /api/health"


# ── 4. Production Healthcheck & Uptime Verification ───────────────────────────

@pytest.mark.asyncio
async def test_production_health_endpoint(client):
    """Verify /api/health returns HTTP 200 with complete operational metadata."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "ok"
    assert "app" in data
    assert "version" in data
    assert "uptime_seconds" in data
    assert data["guardrails"] == "active"
    assert data["monitoring"] == "active"
