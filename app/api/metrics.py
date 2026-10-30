"""
Metrics router — Phase 15 monitoring endpoints.

GET /api/metrics        — Prometheus-compatible text format
GET /api/metrics/json   — Full JSON snapshot for dashboard
"""

import logging
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.services.monitoring_service import get_monitoring_service

router = APIRouter(prefix="/api", tags=["Monitoring"])
logger = logging.getLogger(__name__)


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus-compatible metrics scrape endpoint",
)
async def get_prometheus_metrics() -> str:
    """
    Returns platform metrics in Prometheus text exposition format.
    Compatible with Prometheus scrape configs and Grafana data sources.
    """
    svc = get_monitoring_service()
    return svc.get_prometheus_text()


@router.get(
    "/metrics/json",
    summary="Full JSON metrics snapshot for the dashboard",
)
async def get_metrics_json() -> dict:
    """
    Returns the complete metrics snapshot as a JSON object.
    Used by the frontend Monitoring tab and CI health checks.
    """
    svc = get_monitoring_service()
    return svc.get_metrics_json()
