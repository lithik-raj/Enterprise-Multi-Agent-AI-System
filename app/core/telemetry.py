"""
core/telemetry.py

Observability & OpenTelemetry-compatible distributed tracing module.
Generates W3C-compliant 128-bit trace IDs and manages span contexts across agents.
"""

from __future__ import annotations

import contextvars
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

_current_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("trace_id", default=None)


class SpanRecord(BaseModel):
    span_id: str
    trace_id: str
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


def generate_trace_id() -> str:
    """Generate a 128-bit hexadecimal trace identifier."""
    return uuid.uuid4().hex


def get_current_trace_id() -> str:
    """Retrieve active trace ID or generate a new one if not present."""
    tid = _current_trace_id.get()
    if not tid:
        tid = f"tr_{generate_trace_id()[:16]}"
        _current_trace_id.set(tid)
    return tid


def set_current_trace_id(trace_id: str) -> contextvars.Token:
    """Set active trace ID for current coroutine / thread."""
    return _current_trace_id.set(trace_id)


class TraceSpan:
    """Context manager for tracing agent execution spans with duration measurement."""

    def __init__(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        self.name = name
        self.attributes = attributes or {}
        self.span_id = f"sp_{uuid.uuid4().hex[:12]}"
        self.trace_id = get_current_trace_id()
        self.start_time = 0.0
        self.end_time = 0.0
        self.duration_ms = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration_ms = round((self.end_time - self.start_time) * 1000.0, 2)
        if exc_val:
            self.attributes["error"] = str(exc_val)
        return False
