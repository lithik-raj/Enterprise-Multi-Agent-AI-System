"""
Tests to verify Vercel serverless deployment readiness.
Ensures api/index.py entrypoint, routing, static asset serving, and health checks pass.
"""

import json
from pathlib import Path
from fastapi.testclient import TestClient
from api.index import app


def test_vercel_entrypoint_health():
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "Enterprise Multi-Agent AI" in data["app"]


def test_vercel_static_frontend_serving():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "<!DOCTYPE html>" in resp.text
    assert "Enterprise Multi-Agent AI" in resp.text


def test_vercel_css_asset_serving():
    client = TestClient(app)
    resp = client.get("/css/styles.css")
    assert resp.status_code == 200
    assert "text/css" in resp.headers.get("content-type", "")


def test_vercel_json_configuration():
    vpath = Path(__file__).resolve().parent.parent / "vercel.json"
    assert vpath.exists(), "vercel.json must exist in repository root"
    with open(vpath, "r", encoding="utf-8") as f:
        vcfg = json.load(f)
    assert vcfg.get("version") == 2
    assert "rewrites" in vcfg
    assert any(r.get("destination") == "/api/index.py" for r in vcfg["rewrites"])
