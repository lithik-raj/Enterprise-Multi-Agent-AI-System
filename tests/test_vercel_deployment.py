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


def test_vercel_js_asset_serving():
    client = TestClient(app)
    resp = client.get("/js/app.js")
    assert resp.status_code == 200
    assert "javascript" in resp.headers.get("content-type", "")


def test_vercel_internal_rewrite_routes():
    client = TestClient(app)
    # Test that requests routed to /api/index.py or /api/index render the frontend live demo
    resp_py = client.get("/api/index.py")
    assert resp_py.status_code == 200
    assert "text/html" in resp_py.headers.get("content-type", "")
    assert "<!DOCTYPE html>" in resp_py.text

    resp_idx = client.get("/api/index")
    assert resp_idx.status_code == 200
    assert "text/html" in resp_idx.headers.get("content-type", "")


def test_vercel_json_configuration():
    vpath = Path(__file__).resolve().parent.parent / "vercel.json"
    assert vpath.exists(), "vercel.json must exist in repository root"
    with open(vpath, "r", encoding="utf-8") as f:
        vcfg = json.load(f)
    assert vcfg.get("version") == 2
    assert "rewrites" in vcfg
    assert any(r.get("destination") == "/api/index.py" for r in vcfg["rewrites"])


def test_vercel_matched_path_rewrites():
    client = TestClient(app)
    # When Vercel rewrites to /api/index.py with x-forwarded-uri header (standard proxy behavior)
    health_fwd = client.get("/api/index.py", headers={"x-forwarded-uri": "/api/health"})
    assert health_fwd.status_code == 200
    assert health_fwd.json().get("status") == "ok"

    # When Vercel rewrites to /api/index.py with x-matched-path header
    css_resp = client.get("/api/index.py", headers={"x-matched-path": "/css/styles.css"})
    assert css_resp.status_code == 200
    assert "text/css" in css_resp.headers.get("content-type", "")

    js_resp = client.get("/api/index.py", headers={"x-matched-path": "/js/app.js"})
    assert js_resp.status_code == 200
    assert "javascript" in js_resp.headers.get("content-type", "")

    health_resp = client.get("/api/index.py", headers={"x-matched-path": "/api/health"})
    assert health_resp.status_code == 200
    assert health_resp.json().get("status") == "ok"



def test_public_directory_assets_exist():
    root = Path(__file__).resolve().parent.parent
    pub = root / "public"
    assert pub.exists(), "public directory must exist for Vercel Edge CDN asset serving"
    assert (pub / "index.html").exists()
    assert (pub / "css" / "styles.css").exists()
    assert (pub / "js" / "app.js").exists()
    assert (pub / "js" / "api.js").exists()
    assert (pub / "js" / "three.min.js").exists()
    assert (pub / "js" / "quantum-universe.js").exists()


def test_frontend_key_elements_integrity():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    # Verify Azure / LLM Key configuration controls
    assert 'id="azure-topbar-pill"' in html
    assert 'id="azure-pill-label"' in html
    assert 'id="chat-configure-azure-btn"' in html
    assert 'id="chat-model-badge"' in html
    assert 'id="azure-config-modal"' in html
    assert 'id="azure-modal-key"' in html
    assert 'id="azure-modal-save-btn"' in html
    assert 'id="azure-modal-test-btn"' in html
    # Verify 1-click Demo credentials and auth tabs
    assert 'id="btn-fill-hr-admin"' in html
    assert 'id="btn-fill-recruiter"' in html
    assert 'id="btn-copy-pass"' in html
    assert 'id="auth-tab-signin"' in html
    assert 'id="auth-tab-signup"' in html
    assert 'id="hr-signup-form"' in html

