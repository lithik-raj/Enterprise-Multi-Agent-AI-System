"""
Request Timing Middleware.

ASGI middleware that:
  1. Records request latency for every route
  2. Adds X-Request-ID header for distributed tracing
  3. Adds X-Process-Time header to every response
  4. Feeds metrics into MonitoringService

Phase 15 — Production hardening.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.monitoring_service import get_monitoring_service

logger = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Lightweight ASGI middleware for request-level observability.

    Adds to every response:
      - X-Request-ID: unique request identifier (UUID4)
      - X-Process-Time: wall-clock time in milliseconds

    Records to MonitoringService:
      - Route + status_code + latency_ms
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        # Attach request ID for downstream logging
        request.state.request_id = request_id

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            monitoring = get_monitoring_service()
            monitoring.record_request(
                route=request.url.path,
                status_code=500,
                latency_ms=elapsed_ms,
            )
            logger.error(
                "Unhandled exception | request_id=%s path=%s error=%s",
                request_id, request.url.path, exc
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Add observability headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{elapsed_ms:.2f}ms"

        # Record to monitoring service
        monitoring = get_monitoring_service()
        monitoring.record_request(
            route=request.url.path,
            status_code=response.status_code,
            latency_ms=elapsed_ms,
        )

        logger.debug(
            "Request | id=%s method=%s path=%s status=%d latency=%.1fms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )

        return response
