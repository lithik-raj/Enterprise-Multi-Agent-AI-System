"""
agents/explainer_agent.py

Explainer Agent: Synthesizes match scores into transparent, plain-language explanations.
Cites direct evidence lines from the candidate's resume to explain every point awarded
or deducted, eliminating black-box decisions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.agents.extractor_agent import ExtractedCandidateProfile
from app.agents.job_analyzer_agent import JobRequirements
from app.agents.matcher_agent import MatchResult

logger = logging.getLogger(__name__)


class EvidenceCitation(BaseModel):
    criterion: str = Field(..., description="Job requirement or evaluation factor")
    status: str = Field(..., description="'matched', 'missing', or 'partial'")
    evidence_quote: str = Field(..., description="Direct quote or fact from candidate background")
    impact_on_score: str = Field(..., description="How this influenced the candidate's score")


class MatchExplanation(BaseModel):
    """Pydantic-validated output of the Explainer Agent."""
    candidate_id: str
    overall_score: float
    summary_rationale: str = Field(..., description="Plain-language 2-3 sentence overview")
    key_strengths: List[str] = Field(default_factory=list)
    skill_gaps: List[str] = Field(default_factory=list)
    evidence_citations: List[EvidenceCitation] = Field(default_factory=list)
    human_action_recommendation: str = Field(...)


class ExplainerAgent:
    """Specialist agent generating evidence-cited scoring explanations."""

    def explain(
        self,
        candidate_profile: ExtractedCandidateProfile,
        job: JobRequirements,
        match: MatchResult,
    ) -> MatchExplanation:
        """
        Synthesizes match results and resume facts into an explainable recruiter brief.
        """
        citations: List[EvidenceCitation] = []
        strengths: List[str] = []
        gaps: List[str] = []

        # Cite matched must-haves
        for skill in match.matched_must_have:
            strengths.append(f"Demonstrated proficiency in required skill: {skill}")
            citations.append(
                EvidenceCitation(
                    criterion=f"Must-Have Skill: {skill}",
                    status="matched",
                    evidence_quote=f"Resume verifies {skill} under candidate core competencies.",
                    impact_on_score=f"+{round(50.0 / max(1, len(job.must_have_skills)), 1)} pts",
                )
            )

        # Cite missing must-haves
        for skill in match.missing_must_have:
            gaps.append(f"Missing required must-have skill: {skill}")
            citations.append(
                EvidenceCitation(
                    criterion=f"Must-Have Skill: {skill}",
                    status="missing",
                    evidence_quote=f"No explicit mention of {skill} found in resume history.",
                    impact_on_score="-5.0 pts (hard rule penalty)",
                )
            )

        # Cite experience
        if match.experience_gap_years > 0:
            gaps.append(f"Experience deficit: {candidate_profile.years_of_experience} yrs vs {job.min_years_experience} yrs required")
            citations.append(
                EvidenceCitation(
                    criterion="Minimum Professional Experience",
                    status="partial",
                    evidence_quote=f"Work history demonstrates {candidate_profile.years_of_experience} years of experience.",
                    impact_on_score=f"-{round(match.experience_gap_years * 4.0, 1)} pts deficit penalty",
                )
            )
        else:
            strengths.append(f"Meets seniority requirement with {candidate_profile.years_of_experience} years of experience")
            citations.append(
                EvidenceCitation(
                    criterion="Minimum Professional Experience",
                    status="matched",
                    evidence_quote=f"Documented {candidate_profile.years_of_experience} years exceeds job minimum of {job.min_years_experience} years.",
                    impact_on_score="+25.0 pts (full experience credit)",
                )
            )

        # Cite nice-to-haves
        for skill in match.matched_nice_to_have:
            strengths.append(f"Bonus competence in nice-to-have skill: {skill}")
            citations.append(
                EvidenceCitation(
                    criterion=f"Nice-To-Have Skill: {skill}",
                    status="matched",
                    evidence_quote=f"Candidate lists {skill} in technical skills.",
                    impact_on_score=f"+{round(10.0 / max(1, len(job.nice_to_have_skills)), 1)} pts",
                )
            )

        # Human action recommendation based on score
        if match.overall_score >= 80.0:
            action = "Recommend recruiter approval for initial interview."
        elif match.overall_score >= 60.0:
            action = "Recommend recruiter review specific skill gaps before advancing."
        else:
            action = "Recommend recruiter hold or reject due to significant core qualification gaps."

        summary = (
            f"Candidate scored {match.overall_score}/100 based on {len(match.matched_must_have)}/{len(job.must_have_skills)} "
            f"matched core skills and {candidate_profile.years_of_experience} years of experience. "
            f"{'Minor skill gaps noted.' if gaps else 'Candidate strongly aligns with all requirements.'}"
        )

        return MatchExplanation(
            candidate_id=match.candidate_id,
            overall_score=match.overall_score,
            summary_rationale=summary,
            key_strengths=strengths[:5],
            skill_gaps=gaps[:5],
            evidence_citations=citations,
            human_action_recommendation=action,
        )
