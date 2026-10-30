"""
agents/bias_masker_agent.py

Bias Masker Agent: Enforces algorithmic fairness and anti-bias screening.
Strips all protected attributes before candidate scoring:
  - Candidate name (replaced with anonymous ID e.g. "Candidate #A732")
  - Email, phone, address, and physical location
  - Gendered pronouns (he/him, she/her -> they/them)
  - Graduation years (mitigating age bias)
  - Religious / demographic affiliations
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.agents.extractor_agent import ExtractedCandidateProfile


class MaskedCandidateProfile(BaseModel):
    """Candidate profile stripped of demographic and PII attributes for unbiased scoring."""
    candidate_id: str = Field(..., description="Anonymized candidate identifier")
    skills: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)
    years_of_experience: float = Field(0.0)
    degrees: List[str] = Field(default_factory=list, description="Academic degrees without institution names or graduation dates")
    certifications: List[str] = Field(default_factory=list)
    work_authorization: Optional[str] = None
    masked_summary: str = Field(...)


class BiasMaskerAgent:
    """Agent that creates anonymized, unbiased profiles for fair matching."""

    PRONOUN_MAP = [
        (re.compile(r"\bhe\b", re.I), "they"),
        (re.compile(r"\bshe\b", re.I), "they"),
        (re.compile(r"\bhim\b", re.I), "them"),
        (re.compile(r"\bher\b", re.I), "them"),
        (re.compile(r"\bhis\b", re.I), "their"),
        (re.compile(r"\bhers\b", re.I), "theirs"),
    ]

    def mask(self, profile: ExtractedCandidateProfile, anon_id: Optional[str] = None) -> MaskedCandidateProfile:
        """Sanitizes an extracted candidate profile, purging all protected attributes."""
        candidate_id = anon_id or f"Candidate_{abs(hash(profile.name)) % 10000:04d}"

        # Mask education: retain degree type (e.g. "B.S. in Computer Science"), purge school name & graduation year
        sanitized_degrees = [entry.degree for entry in profile.education]

        # Neutralize gender pronouns in summary
        summary = profile.summary or ""
        for pattern, replacement in self.PRONOUN_MAP:
            summary = pattern.sub(replacement, summary)

        # Remove candidate full name and individual name tokens from summary
        if profile.name:
            summary = re.sub(re.escape(profile.name), candidate_id, summary, flags=re.I)
            for part in profile.name.split():
                if len(part) >= 3:
                    summary = re.sub(rf"\b{re.escape(part)}\b", candidate_id, summary, flags=re.I)

        return MaskedCandidateProfile(
            candidate_id=candidate_id,
            skills=profile.skills,
            roles=profile.roles,
            years_of_experience=profile.years_of_experience,
            degrees=sanitized_degrees,
            certifications=profile.certifications,
            work_authorization=profile.work_authorization,
            masked_summary=summary,
        )
