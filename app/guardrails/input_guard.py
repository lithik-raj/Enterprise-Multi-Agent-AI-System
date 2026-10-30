"""
Input Guardrail.

Validates user input BEFORE it reaches the agent pipeline.

Checks:
  1. Length bounds (min/max token count)
  2. Prompt injection detection (LLM jailbreak patterns)
  3. PII scrubbing (email, phone, SSN, credit-card patterns)
  4. Toxic / profanity keyword filter
  5. Policy blocklist (competitor brand names, restricted topics)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


# ── Compiled regex patterns ────────────────────────────────────────────────────

# Prompt injection / jailbreak patterns
_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+(instructions?|prompts?)", re.I),
    re.compile(r"disregard\s+(all\s+)?previous", re.I),
    re.compile(r"you\s+are\s+now\s+(a\s+)?DAN", re.I),
    re.compile(r"act\s+as\s+(if\s+you\s+are\s+)?a\s+(human|person|real\s+AI)", re.I),
    re.compile(r"bypass\s+(safety|filter|policy|guardrail)", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"(system\s*prompt|prompt\s*injection)", re.I),
    re.compile(r"forget\s+(your\s+)?(training|instructions|rules)", re.I),
    re.compile(r"\[INST\]|\[\/INST\]|<\|im_start\|>|<\|im_end\|>"),  # raw LLM tokens
    re.compile(r"IGNORE_PREVIOUS|###\s*NEW\s*INSTRUCTION"),
]

# PII patterns — replaced with placeholders
_PII_RULES: List[tuple[re.Pattern, str]] = [
    # Email
    (re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"), "[EMAIL]"),
    # US phone  +1-555-555-5555 / (555) 555-5555 / 555.555.5555
    (re.compile(r"(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}"), "[PHONE]"),
    # SSN  XXX-XX-XXXX
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    # Credit card  XXXX-XXXX-XXXX-XXXX
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[CARD]"),
    # IP address
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "[IP]"),
]

# Basic toxic/profanity keyword list (production systems use ML classifiers)
_TOXIC_KEYWORDS: set[str] = {
    "kill", "murder", "bomb", "terroris", "cocaine", "heroin", "exploit",
    "hack", "malware", "ransomware", "phishing",
}

# Policy blocklist — topics/brands that must not be discussed
_POLICY_BLOCKLIST: set[str] = {
    "competitor_secret", "internal_salary_band",
}


@dataclass
class GuardResult:
    """Result of an input guard check."""
    passed: bool
    sanitized_text: str
    violations: List[str] = field(default_factory=list)
    pii_removed: List[str] = field(default_factory=list)
    risk_score: float = 0.0          # 0.0 (safe) → 1.0 (high risk)

    @property
    def blocked(self) -> bool:
        return not self.passed

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "risk_score": self.risk_score,
            "violations": self.violations,
            "pii_removed": self.pii_removed,
        }


class InputGuard:
    """
    Stateless input guardrail that validates and sanitises a raw user message.

    Usage::

        guard = InputGuard()
        result = guard.check("User message here")
        if result.blocked:
            return {"error": result.violations[0]}
        safe_text = result.sanitized_text
    """

    def __init__(
        self,
        min_chars: int = 3,
        max_chars: int = 4_000,
        allow_pii_scrubbing: bool = True,
        strict_injection: bool = True,
    ):
        self.min_chars = min_chars
        self.max_chars = max_chars
        self.allow_pii_scrubbing = allow_pii_scrubbing
        self.strict_injection = strict_injection

    # ── Public API ───────────────────────────────────────────────────────────

    def check(self, text: str) -> GuardResult:
        """Run all guardrail checks on `text`. Returns a GuardResult."""
        violations: List[str] = []
        pii_removed: List[str] = []
        risk_score = 0.0

        # 1. Length check
        stripped = text.strip()
        if len(stripped) < self.min_chars:
            violations.append(f"Input too short (min {self.min_chars} chars).")
            risk_score = max(risk_score, 0.1)
        if len(stripped) > self.max_chars:
            violations.append(f"Input too long (max {self.max_chars} chars).")
            risk_score = max(risk_score, 0.2)
            stripped = stripped[: self.max_chars]  # truncate before further checks

        # 2. Prompt injection detection
        injection_hits = self._detect_injection(stripped)
        if injection_hits:
            violations.append(
                f"Prompt injection detected: {', '.join(injection_hits)}"
            )
            risk_score = max(risk_score, 0.9)
            logger.warning("Prompt injection attempt blocked: %s", injection_hits)

        # 3. PII scrubbing
        sanitized = stripped
        if self.allow_pii_scrubbing:
            sanitized, found_pii = self._scrub_pii(sanitized)
            pii_removed.extend(found_pii)
            if found_pii:
                risk_score = max(risk_score, 0.3)

        # 4. Toxic keyword check
        toxic_hits = self._detect_toxic(sanitized)
        if toxic_hits:
            violations.append(f"Potentially harmful content: {', '.join(toxic_hits)}")
            risk_score = max(risk_score, 0.7)

        # 5. Policy blocklist
        blocked_hits = self._detect_blocklist(sanitized)
        if blocked_hits:
            violations.append(f"Policy violation: restricted topic detected.")
            risk_score = max(risk_score, 0.8)

        # Determine pass/fail
        # Block only on injection (>0.85) or explicit policy violations
        passed = risk_score < 0.85 and len(stripped) >= self.min_chars

        return GuardResult(
            passed=passed,
            sanitized_text=sanitized if passed else "",
            violations=violations,
            pii_removed=pii_removed,
            risk_score=round(risk_score, 2),
        )

    # ── Private helpers ──────────────────────────────────────────────────────

    def _detect_injection(self, text: str) -> List[str]:
        hits = []
        for pattern in _INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                hits.append(match.group(0)[:50])
        return hits

    def _scrub_pii(self, text: str) -> tuple[str, List[str]]:
        found: List[str] = []
        for pattern, placeholder in _PII_RULES:
            matches = pattern.findall(text)
            if matches:
                label = placeholder.strip("[]")
                found.append(f"{label} ({len(matches)} instance(s))")
                text = pattern.sub(placeholder, text)
        return text, found

    def _detect_toxic(self, text: str) -> List[str]:
        lower = text.lower()
        return [kw for kw in _TOXIC_KEYWORDS if kw in lower]

    def _detect_blocklist(self, text: str) -> List[str]:
        lower = text.lower()
        return [kw for kw in _POLICY_BLOCKLIST if kw in lower]


# ── Module-level singleton ─────────────────────────────────────────────────────
_guard: Optional[InputGuard] = None


def get_input_guard() -> InputGuard:
    global _guard
    if _guard is None:
        _guard = InputGuard()
    return _guard
