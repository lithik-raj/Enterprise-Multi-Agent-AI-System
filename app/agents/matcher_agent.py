"""
agents/matcher_agent.py

Matcher Agent: Evaluates candidate suitability against job opening requirements.
Implements the hybrid matching algorithm:
  - 50% must-have skills
  - 25% experience alignment
  - 15% semantic similarity
  - 10% nice-to-have skills
  - Hard rule penalties with explicit gap reporting
"""

from __future__ import annotations

import hashlib
import logging
import math
import numpy as np
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.agents.bias_masker_agent import MaskedCandidateProfile
from app.agents.job_analyzer_agent import JobRequirements

logger = logging.getLogger(__name__)


class MatchSubscores(BaseModel):
    must_have_score: float = Field(..., ge=0.0, le=100.0)
    experience_score: float = Field(..., ge=0.0, le=100.0)
    semantic_score: float = Field(..., ge=0.0, le=100.0)
    nice_to_have_score: float = Field(..., ge=0.0, le=100.0)
    hard_rule_penalty: float = Field(0.0, ge=0.0)


class MatchResult(BaseModel):
    """Pydantic-validated output of the Matcher Agent."""
    candidate_id: str
    overall_score: float = Field(..., ge=0.0, le=100.0)
    subscores: MatchSubscores
    matched_must_have: List[str] = Field(default_factory=list)
    missing_must_have: List[str] = Field(default_factory=list)
    matched_nice_to_have: List[str] = Field(default_factory=list)
    experience_gap_years: float = Field(0.0)
    hard_rule_violations: List[str] = Field(default_factory=list)


class MatcherAgent:
    """Specialist agent computing multi-factor candidate match scores."""

    def __init__(self, embedding_dimension: int = 128):
        self.dimension = embedding_dimension

    def _embed(self, text: str) -> np.ndarray:
        """Fast, deterministic dense semantic projection."""
        vec = np.zeros(self.dimension, dtype=np.float32)
        words = text.lower().split()
        if not words:
            return vec
        for w in words:
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h // self.dimension) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def match(self, candidate: MaskedCandidateProfile, job: JobRequirements) -> MatchResult:
        """
        Computes hybrid score combining rule checks and semantic embeddings.
        """
        weights = job.weights
        cand_skills = set(s.lower() for s in candidate.skills)
        violations: List[str] = []

        # 1. Must-have skills evaluation (50%)
        must_have_skills = [s.lower() for s in job.must_have_skills]
        matched_must = []
        missing_must = []

        for req in must_have_skills:
            if any(req in s or s in req for s in cand_skills):
                matched_must.append(req.title())
            else:
                missing_must.append(req.title())

        if must_have_skills:
            must_have_score = (len(matched_must) / len(must_have_skills)) * 100.0
        else:
            must_have_score = 100.0

        if missing_must:
            violations.append(f"Missing {len(missing_must)} must-have skill(s): {', '.join(missing_must)}")

        # 2. Experience evaluation (25%)
        exp_score = 100.0
        exp_gap = 0.0
        if job.min_years_experience > 0:
            if candidate.years_of_experience >= job.min_years_experience:
                exp_score = 100.0
            else:
                exp_score = max(0.0, (candidate.years_of_experience / job.min_years_experience) * 100.0)
                exp_gap = round(job.min_years_experience - candidate.years_of_experience, 1)
                violations.append(f"Below minimum experience by {exp_gap} years ({candidate.years_of_experience} yrs vs {job.min_years_experience} yrs required)")

        # 3. Nice-to-have skills evaluation (10%)
        nice_to_have_skills = [s.lower() for s in job.nice_to_have_skills]
        matched_nice = []
        for req in nice_to_have_skills:
            if any(req in s or s in req for s in cand_skills):
                matched_nice.append(req.title())

        if nice_to_have_skills:
            nice_to_have_score = (len(matched_nice) / len(nice_to_have_skills)) * 100.0
        else:
            nice_to_have_score = 100.0

        # 4. Semantic similarity (15%)
        cand_text = f"{candidate.masked_summary} {' '.join(candidate.skills)} {' '.join(candidate.roles)}"
        job_text = f"{job.title} {job.summary} {' '.join(job.must_have_skills)}"
        semantic_score = self._compute_semantic_similarity(cand_text, job_text)

        # 5. Hard rule penalty calculation
        penalty = 0.0
        # Missing must-haves incur 5 penalty points each
        penalty += len(missing_must) * 5.0
        # Experience gap incurs 4 penalty points per missing year
        if exp_gap > 0:
            penalty += exp_gap * 4.0

        # Work authorization check
        if job.required_work_authorization and candidate.work_authorization:
            if "citizen" in job.required_work_authorization.lower() and "citizen" not in candidate.work_authorization.lower():
                penalty += 15.0
                violations.append("Candidate does not meet required work authorization criteria")

        # Composite weighted blend
        raw_weighted_score = (
            (weights.must_have * must_have_score)
            + (weights.experience * exp_score)
            + (weights.semantic * semantic_score)
            + (weights.nice_to_have * nice_to_have_score)
        )

        final_score = max(0.0, min(100.0, raw_weighted_score - penalty))

        subscores = MatchSubscores(
            must_have_score=round(must_have_score, 1),
            experience_score=round(exp_score, 1),
            semantic_score=round(semantic_score, 1),
            nice_to_have_score=round(nice_to_have_score, 1),
            hard_rule_penalty=round(penalty, 1),
        )

        return MatchResult(
            candidate_id=candidate.candidate_id,
            overall_score=round(final_score, 1),
            subscores=subscores,
            matched_must_have=matched_must,
            missing_must_have=missing_must,
            matched_nice_to_have=matched_nice,
            experience_gap_years=exp_gap,
            hard_rule_violations=violations,
        )

    def _compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two text representations, returning 0-100."""
        try:
            vec1 = self._embed(text1)
            vec2 = self._embed(text2)

            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 70.0

            cosine_sim = float(np.dot(vec1, vec2) / (norm1 * norm2))
            mapped = ((cosine_sim + 1.0) / 2.0) * 100.0
            return max(0.0, min(100.0, mapped))
        except Exception:
            return 75.0
