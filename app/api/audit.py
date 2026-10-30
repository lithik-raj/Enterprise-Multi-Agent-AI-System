"""
Audit Trail & System Observability Router — Phase 24.

Exposes REST endpoints for platform-wide audit event queries:
  GET  /api/audit/trail       — Retrieve recent audit trail events
  GET  /api/audit/stats       — Get aggregated audit statistics
  POST /api/audit/record      — Manually record a custom audit event
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from app.services.audit_service import get_audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit", tags=["Audit Trail & Observability"])


class RecordEventRequest(BaseModel):
    category: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=3, max_length=500)
    details: str = Field(default="", max_length=2000)
    severity: str = Field(default="info", pattern="^(info|warning|error|critical)$")
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.get(
    "/trail",
    summary="Retrieve recent audit trail events",
    status_code=status.HTTP_200_OK,
)
async def get_audit_trail(
    limit: int = Query(default=50, ge=1, le=200),
    category: Optional[str] = Query(default=None),
) -> List[Dict[str, Any]]:
    """Returns the most recent audit events, optionally filtered by category."""
    service = get_audit_service()
    return service.get_trail(limit=limit, category=category)


@router.get(
    "/stats",
    summary="Get aggregated audit trail statistics",
    status_code=status.HTTP_200_OK,
)
async def get_audit_stats() -> Dict[str, Any]:
    """Returns category-level aggregated statistics for all recorded events."""
    service = get_audit_service()
    return service.get_stats()


@router.post(
    "/record",
    summary="Record a custom audit event",
    status_code=status.HTTP_201_CREATED,
)
async def record_audit_event(request: RecordEventRequest) -> Dict[str, Any]:
    """Manually records a custom audit event into the trail."""
    service = get_audit_service()
    event = service.record(
        category=request.category,
        action=request.action,
        details=request.details,
        severity=request.severity,
        metadata=request.metadata,
    )
    return {"status": "recorded", "event_id": event.event_id}
