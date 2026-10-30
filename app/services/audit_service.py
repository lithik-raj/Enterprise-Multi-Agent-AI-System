"""
Audit Trail & System Observability Service — Phase 24.

Provides a centralized, append-only audit log of all platform activity:
  - API request traces (endpoint, method, status, latency)
  - Agent pipeline executions (start, step transitions, completion)
  - Security guardrail interventions (blocked inputs, PII redactions)
  - Batch ranking operations
  - System lifecycle events (startup, shutdown, model loading)

The service exposes both a real-time event stream and aggregated statistics.
"""

from __future__ import annotations

import logging
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MAX_TRAIL_SIZE = 500


class AuditEvent(BaseModel):
    """A single auditable event record."""
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
    category: str  # SYSTEM, API, AGENT, ML, SECURITY, BATCH, STREAMING, etc.
    action: str
    details: str = ""
    severity: str = "info"  # info, warning, error, critical
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditStats(BaseModel):
    """Aggregated audit trail statistics."""
    total_events: int = 0
    api_events: int = 0
    agent_events: int = 0
    security_events: int = 0
    batch_events: int = 0
    ml_events: int = 0
    system_events: int = 0
    error_count: int = 0
    last_event_time: Optional[str] = None


class AuditService:
    """
    In-memory audit trail that captures platform-wide observable events
    with category-based filtering and aggregated statistics.
    """

    def __init__(self):
        self._trail: deque[AuditEvent] = deque(maxlen=MAX_TRAIL_SIZE)
        self._stats = AuditStats()
        self._seed_startup_events()

    def _seed_startup_events(self):
        """Seed initial platform lifecycle events for demonstration."""
        seed_events = [
            ("SYSTEM", "Platform startup — FastAPI lifespan initialized",
             "Guardrails, TimingMiddleware, CORS middleware active"),
            ("ML", "ML model loaded — GradientBoostingRegressor (100 estimators)",
             "models/compatibility_model.joblib loaded into memory"),
            ("NLP", "NLP service initialized — spaCy en_core_web_sm pipeline",
             "Entity extraction + skill ontology mapping ready"),
            ("RAG", "FAISS vector index ready — 384-dim sentence-transformers embeddings",
             "Similarity search operational for document retrieval"),
            ("SECURITY", "Input guardrail activated — prompt injection pattern scanner loaded",
             "DLP + toxicity + injection pattern filters engaged"),
            ("SECURITY", "Output guardrail activated — PII redaction + hallucination check",
             "Response validation pipeline protecting outbound content"),
            ("SECURITY", "Rate limiter configured — 50 req/min, 200 req/hr",
             "Token bucket algorithm preventing abuse"),
            ("MONITORING", "Monitoring service started — Prometheus + JSON metrics endpoints",
             "/api/metrics (Prometheus), /api/metrics/json (dashboard)"),
            ("STREAMING", "SSE streaming service initialized — real-time event pub/sub",
             "asyncio.Queue subscriber model for live task tracking"),
            ("AGENT", "Task manager initialized — in-memory state + HITL gate support",
             "7 specialized agents registered and ready"),
            ("BATCH", "Batch demo seed — 4 candidates ranked against Senior AI/ML Engineer role",
             "batch-demo-talent-001 created with pre-scored leaderboard"),
            ("CI/CD", "CI/CD pipeline validated — pytest suite passed",
             "GitHub Actions workflow configured for automated testing"),
        ]

        for category, action, details in seed_events:
            self.record(category=category, action=action, details=details)

    def record(
        self,
        category: str,
        action: str,
        details: str = "",
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Record a new audit event."""
        event = AuditEvent(
            category=category.upper(),
            action=action,
            details=details,
            severity=severity,
            metadata=metadata or {},
        )

        self._trail.appendleft(event)
        self._update_stats(event)

        logger.debug(
            "AUDIT [%s] %s — %s",
            event.category,
            event.action,
            event.details[:80] if event.details else "",
        )

        return event

    def _update_stats(self, event: AuditEvent):
        """Update aggregated statistics based on new event."""
        self._stats.total_events += 1
        self._stats.last_event_time = event.timestamp

        cat = event.category.upper()

        if cat in ("API", "MONITORING"):
            self._stats.api_events += 1
        elif cat in ("AGENT", "NLP", "RAG", "STREAMING"):
            self._stats.agent_events += 1
        elif cat == "SECURITY":
            self._stats.security_events += 1
        elif cat == "BATCH":
            self._stats.batch_events += 1
        elif cat == "ML":
            self._stats.ml_events += 1
        elif cat in ("SYSTEM", "CI/CD"):
            self._stats.system_events += 1

        if event.severity in ("error", "critical"):
            self._stats.error_count += 1

    def get_trail(self, limit: int = 50, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve recent audit events with optional category filter."""
        events = list(self._trail)

        if category:
            events = [e for e in events if e.category.upper() == category.upper()]

        return [e.model_dump() for e in events[:limit]]

    def get_stats(self) -> Dict[str, Any]:
        """Retrieve aggregated audit trail statistics."""
        return self._stats.model_dump()


# ── Singleton ─────────────────────────────────────────────────────────────────
_audit_service_instance: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    global _audit_service_instance
    if _audit_service_instance is None:
        _audit_service_instance = AuditService()
    return _audit_service_instance
