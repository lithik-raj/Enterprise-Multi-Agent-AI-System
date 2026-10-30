"""
Monitoring & Observability Service.

Tracks:
  - Request counts (total / per-route / per-status)
  - Latency histograms (P50, P90, P99)
  - Agent pipeline step timings
  - Guardrail trigger events
  - Error rates
  - Active task counts

Exposes metrics via GET /api/metrics (Prometheus-compatible text format)
and GET /api/metrics/json (JSON format for dashboard).
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LatencyBucket:
    """Rolling window of latency samples (last 1000 requests)."""
    samples: Deque[float] = field(default_factory=lambda: deque(maxlen=1000))

    def record(self, latency_ms: float) -> None:
        self.samples.append(latency_ms)

    def percentile(self, p: float) -> float:
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * p / 100)
        return round(sorted_samples[min(idx, len(sorted_samples) - 1)], 2)

    @property
    def p50(self) -> float:
        return self.percentile(50)

    @property
    def p90(self) -> float:
        return self.percentile(90)

    @property
    def p99(self) -> float:
        return self.percentile(99)

    @property
    def mean(self) -> float:
        if not self.samples:
            return 0.0
        return round(sum(self.samples) / len(self.samples), 2)


class MonitoringService:
    """
    Thread-safe in-memory metrics collector.

    In production, swap for Prometheus + Grafana.
    """

    def __init__(self):
        self._lock = Lock()
        self._started_at: float = time.monotonic()

        # Request counters
        self._request_counts: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._status_counts: Dict[int, int] = defaultdict(int)

        # Latency tracking per route
        self._latencies: Dict[str, LatencyBucket] = defaultdict(LatencyBucket)

        # Guardrail events
        self._guardrail_blocks: int = 0
        self._rate_limit_hits: int = 0
        self._pii_scrub_events: int = 0

        # Agent pipeline metrics
        self._pipeline_runs: int = 0
        self._pipeline_successes: int = 0
        self._pipeline_failures: int = 0
        self._agent_step_timings: Dict[str, LatencyBucket] = defaultdict(LatencyBucket)

    # ── Request tracking ─────────────────────────────────────────────────────

    def record_request(
        self, route: str, status_code: int, latency_ms: float
    ) -> None:
        with self._lock:
            self._request_counts[route] += 1
            self._status_counts[status_code] += 1
            self._latencies[route].record(latency_ms)
            if status_code >= 500:
                self._error_counts[route] += 1

    def record_guardrail_block(self) -> None:
        with self._lock:
            self._guardrail_blocks += 1

    def record_rate_limit_hit(self) -> None:
        with self._lock:
            self._rate_limit_hits += 1

    def record_pii_scrub(self) -> None:
        with self._lock:
            self._pii_scrub_events += 1

    def record_pipeline_run(self, success: bool) -> None:
        with self._lock:
            self._pipeline_runs += 1
            if success:
                self._pipeline_successes += 1
            else:
                self._pipeline_failures += 1

    def record_agent_step(self, agent_name: str, latency_ms: float) -> None:
        with self._lock:
            self._agent_step_timings[agent_name].record(latency_ms)

    # ── Snapshots ────────────────────────────────────────────────────────────

    def get_metrics_json(self) -> Dict[str, Any]:
        """Return complete metrics snapshot as JSON-serialisable dict."""
        with self._lock:
            uptime_s = time.monotonic() - self._started_at
            total_requests = sum(self._request_counts.values())
            total_errors = sum(self._error_counts.values())

            route_stats = {}
            for route, bucket in self._latencies.items():
                route_stats[route] = {
                    "requests": self._request_counts[route],
                    "errors": self._error_counts[route],
                    "latency_ms": {
                        "mean": bucket.mean,
                        "p50": bucket.p50,
                        "p90": bucket.p90,
                        "p99": bucket.p99,
                    },
                }

            agent_stats = {}
            for agent, bucket in self._agent_step_timings.items():
                agent_stats[agent] = {
                    "latency_ms": {
                        "mean": bucket.mean,
                        "p50": bucket.p50,
                        "p90": bucket.p90,
                        "p99": bucket.p99,
                    }
                }

            return {
                "uptime_seconds": round(uptime_s, 1),
                "requests": {
                    "total": total_requests,
                    "errors": total_errors,
                    "error_rate": round(total_errors / max(total_requests, 1), 4),
                    "by_status": dict(self._status_counts),
                    "by_route": route_stats,
                },
                "guardrails": {
                    "blocks": self._guardrail_blocks,
                    "rate_limit_hits": self._rate_limit_hits,
                    "pii_scrub_events": self._pii_scrub_events,
                },
                "pipeline": {
                    "total_runs": self._pipeline_runs,
                    "successes": self._pipeline_successes,
                    "failures": self._pipeline_failures,
                    "success_rate": round(
                        self._pipeline_successes / max(self._pipeline_runs, 1), 4
                    ),
                    "agents": agent_stats,
                },
            }

    def get_prometheus_text(self) -> str:
        """Return basic Prometheus-compatible text format."""
        data = self.get_metrics_json()
        lines: List[str] = [
            "# HELP nexusagent_requests_total Total HTTP requests",
            "# TYPE nexusagent_requests_total counter",
            f"nexusagent_requests_total {data['requests']['total']}",
            "",
            "# HELP nexusagent_errors_total Total HTTP 5xx errors",
            "# TYPE nexusagent_errors_total counter",
            f"nexusagent_errors_total {data['requests']['errors']}",
            "",
            "# HELP nexusagent_guardrail_blocks_total Guardrail block events",
            "# TYPE nexusagent_guardrail_blocks_total counter",
            f"nexusagent_guardrail_blocks_total {data['guardrails']['blocks']}",
            "",
            "# HELP nexusagent_rate_limit_hits_total Rate limit hits",
            "# TYPE nexusagent_rate_limit_hits_total counter",
            f"nexusagent_rate_limit_hits_total {data['guardrails']['rate_limit_hits']}",
            "",
            "# HELP nexusagent_pipeline_runs_total Total agent pipeline runs",
            "# TYPE nexusagent_pipeline_runs_total counter",
            f"nexusagent_pipeline_runs_total {data['pipeline']['total_runs']}",
            "",
            "# HELP nexusagent_uptime_seconds Platform uptime in seconds",
            "# TYPE nexusagent_uptime_seconds gauge",
            f"nexusagent_uptime_seconds {data['uptime_seconds']}",
        ]

        # Per-route latency
        for route, stats in data["requests"]["by_route"].items():
            safe_route = route.replace("/", "_").replace("-", "_").lstrip("_")
            lines += [
                "",
                f"# HELP nexusagent_latency_p99_ms_{safe_route} P99 latency ms",
                f"# TYPE nexusagent_latency_p99_ms_{safe_route} gauge",
                f"nexusagent_latency_p99_ms_{safe_route} {stats['latency_ms']['p99']}",
            ]

        return "\n".join(lines) + "\n"


# ── Singleton ──────────────────────────────────────────────────────────────────
_monitoring: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    global _monitoring
    if _monitoring is None:
        _monitoring = MonitoringService()
    return _monitoring
