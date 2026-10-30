"""
Token-bucket Rate Limiter.

Provides per-client request throttling to protect the AI pipeline from
abuse, runaway automation, and cost overruns.

Design:
  - Token-bucket algorithm (smooth burst tolerance)
  - Per-IP / per-session key
  - In-memory storage (swap for Redis in production)
  - FastAPI middleware integration
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Bucket:
    """Token-bucket state for a single client."""
    tokens: float
    last_refill: float = field(default_factory=time.monotonic)


class RateLimiter:
    """
    In-memory token-bucket rate limiter.

    Args:
        max_tokens:     Maximum burst capacity per client.
        refill_rate:    Tokens added per second.
        cost_per_call:  Tokens consumed per API call.

    Usage::

        limiter = RateLimiter(max_tokens=10, refill_rate=2, cost_per_call=1)
        allowed, info = limiter.check("192.168.1.1")
        if not allowed:
            raise HTTPException(429, detail=info["message"])
    """

    def __init__(
        self,
        max_tokens: float = 10.0,
        refill_rate: float = 2.0,       # tokens / second
        cost_per_call: float = 1.0,
    ):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.cost_per_call = cost_per_call
        self._buckets: Dict[str, Bucket] = defaultdict(
            lambda: Bucket(tokens=max_tokens)
        )
        self._lock = Lock()

    # ── Public API ───────────────────────────────────────────────────────────

    def check(self, client_key: str) -> Tuple[bool, dict]:
        """
        Check if `client_key` is within rate limits and consume one token.

        Returns:
            (allowed: bool, info: dict with tokens_remaining & retry_after)
        """
        with self._lock:
            bucket = self._buckets[client_key]
            self._refill(bucket)

            if bucket.tokens >= self.cost_per_call:
                bucket.tokens -= self.cost_per_call
                logger.debug(
                    "RateLimit ALLOW key=%s tokens_left=%.1f",
                    client_key, bucket.tokens
                )
                return True, {
                    "allowed": True,
                    "tokens_remaining": round(bucket.tokens, 1),
                    "limit": self.max_tokens,
                    "refill_rate": self.refill_rate,
                }
            else:
                retry_after = (
                    (self.cost_per_call - bucket.tokens) / self.refill_rate
                )
                logger.warning(
                    "RateLimit BLOCK key=%s retry_after=%.1fs", client_key, retry_after
                )
                return False, {
                    "allowed": False,
                    "tokens_remaining": round(bucket.tokens, 1),
                    "limit": self.max_tokens,
                    "retry_after_seconds": round(retry_after, 1),
                    "message": (
                        f"Rate limit exceeded. Retry after {retry_after:.1f}s."
                    ),
                }

    def reset(self, client_key: str) -> None:
        """Reset a specific client's bucket (useful for testing)."""
        with self._lock:
            self._buckets[client_key] = Bucket(tokens=self.max_tokens)

    def stats(self) -> dict:
        """Return aggregate limiter statistics."""
        with self._lock:
            return {
                "active_clients": len(self._buckets),
                "max_tokens": self.max_tokens,
                "refill_rate": self.refill_rate,
                "cost_per_call": self.cost_per_call,
            }

    # ── Private helpers ──────────────────────────────────────────────────────

    def _refill(self, bucket: Bucket) -> None:
        now = time.monotonic()
        elapsed = now - bucket.last_refill
        added = elapsed * self.refill_rate
        bucket.tokens = min(self.max_tokens, bucket.tokens + added)
        bucket.last_refill = now


# ── Singleton instances (one per route group) ─────────────────────────────────
_chat_limiter: Optional[RateLimiter] = None
_analyze_limiter: Optional[RateLimiter] = None


def get_rate_limiter(route: str = "chat") -> RateLimiter:
    """Return the singleton rate limiter for the given route."""
    global _chat_limiter, _analyze_limiter

    if route == "analyze":
        if _analyze_limiter is None:
            # Stricter for the heavy multi-agent pipeline
            _analyze_limiter = RateLimiter(max_tokens=5, refill_rate=0.5)
        return _analyze_limiter

    if _chat_limiter is None:
        _chat_limiter = RateLimiter(max_tokens=20, refill_rate=3)
    return _chat_limiter
