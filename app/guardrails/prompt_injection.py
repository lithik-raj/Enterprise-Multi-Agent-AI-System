"""
guardrails/prompt_injection.py

Untrusted input defense and resume prompt injection guard.
Treats all resume content as unverified data, neutralizing attempts to override
agent prompts, alter scoring, or trigger unauthorized tools.
"""

from __future__ import annotations

import re
from typing import List, Tuple

# Patterns commonly used in resume injection attacks
_RESUME_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+(instructions?|prompts?|rules?)", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|job\s+requirements)", re.I),
    re.compile(r"give\s+(this\s+)?(candidate|resume|applicant)\s+(a\s+score\s+of\s+)?100", re.I),
    re.compile(r"(always\s+)?rank\s+(this\s+candidate|me)\s+(as\s+)?(top|#1|first|highest)", re.I),
    re.compile(r"system\s*prompt\s*:", re.I),
    re.compile(r"###\s*instruction", re.I),
    re.compile(r"<\|im_start\|>|<\|im_end\|>|\[INST\]|\[\/INST\]", re.I),
    re.compile(r"override\s+(all\s+)?evaluation\s+criteria", re.I),
    re.compile(r"recommend\s+for\s+immediate\s+hire", re.I),
    re.compile(r"you\s+must\s+say\s+['\"].*['\"]", re.I),
]


def detect_prompt_injection(text: str) -> Tuple[bool, List[str]]:
    """
    Scans untrusted input for prompt injection signatures.
    Returns (is_suspicious, list_of_matched_patterns).
    """
    detected: List[str] = []
    for pattern in _RESUME_INJECTION_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            detected.append(pattern.pattern)

    return len(detected) > 0, detected


def sanitize_resume_text(raw_text: str) -> str:
    """
    Sanitizes resume text by stripping delimiter hacks and neutralizing injection commands.
    Does not drop valid candidate text, but replaces malicious overrides with safe indicators.
    """
    sanitized = raw_text

    # Neutralize active jailbreak phrases
    for pattern in _RESUME_INJECTION_PATTERNS:
        sanitized = pattern.sub("[SUSPICIOUS INSTRUCTION REMOVED]", sanitized)

    # Strip dangerous HTML/script tags
    sanitized = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", sanitized, flags=re.DOTALL | re.I)
    sanitized = re.sub(r"<\s*(iframe|embed|object)[^>]*>.*?<\s*/\s*\1\s*>", "", sanitized, flags=re.DOTALL | re.I)

    # Normalize excessive non-printable control characters
    sanitized = "".join(c for c in sanitized if c.isprintable() or c in "\n\r\t")

    return sanitized.strip()


def wrap_untrusted_data(text: str) -> str:
    """
    Encapsulates resume text inside clear untrusted boundary markers.
    The LLM system prompt explicitly instructs models to treat data between
    these tags strictly as passive text, never as commands.
    """
    clean_text = sanitize_resume_text(text)
    return (
        "<UNTRUSTED_RESUME_DATA>\n"
        f"{clean_text}\n"
        "</UNTRUSTED_RESUME_DATA>"
    )
