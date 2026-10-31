"""
Enterprise Multi-Agent AI Intelligence Platform
FastAPI application entry point.

Phase 15 additions:
  - TimingMiddleware for request observability (X-Request-ID, X-Process-Time)
  - GET /api/metrics   (Prometheus scrape)
  - GET /api/metrics/json  (dashboard JSON)
  - Guardrails integrated at chat & analyze routers
"""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.api import chat, tasks, documents, approval, analyze, metrics, ml, stream, batch, audit, ats, career, llm, tenants, auth, recruiter, privacy, ats_expansion, employees, recovery
from app.database.base import init_db
from app.middleware.timing import TimingMiddleware

settings = get_settings()

# ── Logging ───────────────────────────────────────────────────────────────────
log_level_name = os.getenv("LOG_LEVEL", settings.LOG_LEVEL if settings.LOG_LEVEL != "INFO" else "WARNING").upper()
logging.basicConfig(
    level=getattr(logging, log_level_name, logging.WARNING),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("🚀  %s v%s starting up…", settings.APP_NAME, settings.APP_VERSION)
    try:
        init_db()
        logger.debug("🗄️  Multi-tenant database tables initialized.")
    except Exception as e:
        logger.warning("Database initialization note: %s", e)
    async def _async_warmup():
        try:
            from app.rag.embeddings import get_embedding_service
            from app.rag.vector_store import get_vector_store
            embedder = get_embedding_service()
            get_vector_store(embedder.dimension)
            logger.debug("⚡  FAISS Vector Store & Semantic Embeddings pre-warmed.")
        except Exception as e:
            logger.debug("FAISS warmup note: %s", e)

    import asyncio
    asyncio.create_task(_async_warmup())

    async def _auto_open_browser():
        await asyncio.sleep(0.15)
        try:
            from app.utils.browser import open_platform_browser
            port = int(os.getenv("PORT", "8000"))
            host = os.getenv("HOST", "127.0.0.1")
            display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
            open_platform_browser(f"http://{display_host}:{port}")
        except Exception as e:
            logger.debug("Auto browser open note: %s", e)

    asyncio.create_task(_auto_open_browser())
    yield
    logger.debug("🛑  Application shutting down.")


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "An enterprise-grade multi-agent AI platform for intelligent "
        "decision support powered by LangGraph, RAG, NLP, ML, Guardrails "
        "and Human-in-the-Loop governance."
    ),
    lifespan=lifespan,
)

# ── Middleware stack (order matters: outermost = last added) ───────────────────
app.add_middleware(TimingMiddleware)          # Phase 15: observability
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def vercel_url_normalize_middleware(request, call_next):
    """
    Normalizes internal Vercel serverless function rewrite paths.
    Vercel rewrites often route to `/api/index.py` or `/api/index`;
    this maps root and subpath requests so FastAPI routers match correctly.
    """
    raw_path = request.scope.get("path", "")
    if raw_path in ("/api/index.py", "/api/index", "/api/index/"):
        request.scope["path"] = "/"
    elif raw_path.startswith("/api/index.py/"):
        request.scope["path"] = raw_path[len("/api/index.py"):]
    elif raw_path.startswith("/api/index/"):
        request.scope["path"] = raw_path[len("/api/index"):]
    return await call_next(request)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(tasks.router)
app.include_router(documents.router)
app.include_router(approval.router)
app.include_router(analyze.router)
app.include_router(metrics.router)           # Phase 15: monitoring endpoints
app.include_router(ml.router)                # Phase 19: trained ML model endpoints
app.include_router(stream.router)            # Phase 20: real-time SSE streaming endpoints
app.include_router(batch.router)             # Phase 22: batch multi-candidate ranking endpoints
app.include_router(audit.router)             # Phase 24: audit trail & observability endpoints
app.include_router(ats.router)               # ATS Resume & Score Analyzer endpoints
app.include_router(career.router)            # Live Career & Location Preference Matching endpoints
app.include_router(llm.router)               # Azure OpenAI & LLM runtime configuration endpoints
app.include_router(tenants.router)           # Multi-tenant isolation & provisioning endpoints
app.include_router(auth.router)              # Authentication & RBAC endpoints
app.include_router(recruiter.router)         # Recruiter Dashboard, Screening & Decisions endpoints
app.include_router(privacy.router)           # DPDP & GDPR Compliance endpoints
app.include_router(ats_expansion.router)     # ATS integrations & Internal Mobility endpoints
app.include_router(employees.router)         # Phase 25: Employee Management & Staff Directory
app.include_router(recovery.router)          # Rollback & Recovery (Recycle Bin with 7-Day Retention)





# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Please try again later."},
    )


# ── Health endpoint ───────────────────────────────────────────────────────────
@app.get(
    "/api/health",
    tags=["Health"],
    summary="Platform health check",
)
async def health_check():
    """
    Returns the current operational status of the platform.
    Used by load-balancers, Docker HEALTHCHECK, and CI pipelines.
    """
    from app.services.monitoring_service import get_monitoring_service
    svc = get_monitoring_service()
    m = svc.get_metrics_json()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "uptime_seconds": m["uptime_seconds"],
        "guardrails": "active",
        "monitoring": "active",
    }


# ── Static files & Frontend UI ────────────────────────────────────────────────
from fastapi.responses import FileResponse, HTMLResponse


def _find_frontend_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent / "frontend",
        Path.cwd() / "frontend",
        Path("/var/task/frontend"),
        Path("/var/task/api/frontend"),
        Path(__file__).resolve().parent / "frontend",
    ]
    for p in candidates:
        if p.exists() and (p / "index.html").exists():
            return p
    return candidates[0]


frontend_dir = _find_frontend_dir()


@app.get("/", include_in_schema=False)
@app.get("/api/index.py", include_in_schema=False)
@app.get("/api/index", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
async def serve_index():
    """Serves the main single-page interactive recruitment demo application."""
    idx = _find_frontend_dir() / "index.html"
    if idx.exists():
        return FileResponse(str(idx), media_type="text/html")
    return HTMLResponse("<h1>Enterprise Multi-Agent AI Platform</h1><p>Demo loading...</p>")


@app.get("/css/{filename:path}", include_in_schema=False)
async def serve_css(filename: str):
    """Serves styles and CSS assets."""
    f = _find_frontend_dir() / "css" / filename
    if f.exists():
        return FileResponse(str(f), media_type="text/css")
    return JSONResponse(status_code=404, content={"error": f"CSS asset {filename} not found"})


@app.get("/js/{filename:path}", include_in_schema=False)
async def serve_js(filename: str):
    """Serves scripts, Three.js canvas, and client logic."""
    f = _find_frontend_dir() / "js" / filename
    if f.exists():
        return FileResponse(str(f), media_type="application/javascript")
    return JSONResponse(status_code=404, content={"error": f"JS asset {filename} not found"})


if frontend_dir.exists():
    try:
        app.mount("/frontend", StaticFiles(directory=str(frontend_dir), html=True), name="frontend_dir")
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend_root")
    except Exception:
        pass
