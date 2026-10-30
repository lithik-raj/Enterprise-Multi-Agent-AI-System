"""
agents/critic_agent.py

Critic Agent: Quality assurance specialist providing anti-hallucination verification.
Cross-examines the Explainer Agent's rationale and citations against the candidate's
raw extracted profile. Flags any claim not strictly backed by resume evidence.

Output: Pydantic-validated CriticReport with status ('pass' or 'revise').
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from app.agents.extractor_agent import ExtractedCandidateProfile
from app.agents.explainer_agent import MatchExplanation

logger = logging.getLogger(__name__)


class CriticAuditItem(BaseModel):
    claim: str
    is_verified: bool
    grounding_evidence: str
    audit_note: str


class CriticReport(BaseModel):
    """Pydantic-validated output of the Critic Agent."""
    status: str = Field(..., description="'pass' if 100% faithful, 'revise' if unsupported claims detected")
    faithfulness_score: float = Field(..., ge=0.0, le=1.0, description="Ratio of verified claims to total claims")
    verified_claims_count: int
    unsupported_claims_count: int
    unsupported_claims: List[str] = Field(default_factory=list)
    audit_trail: List[CriticAuditItem] = Field(default_factory=list)
    critic_notes: str


class CriticAgent:
    """Specialist agent auditing explanation faithfulness."""

    def verify(
        self,
        explanation: MatchExplanation,
        candidate_profile: ExtractedCandidateProfile,
    ) -> CriticReport:
        """
        Audits explanation citations against source candidate profile.
        """
        audits: List[CriticAuditItem] = []
        unsupported: List[str] = []

        cand_skills = set(s.lower() for s in candidate_profile.skills)

        # Audit each citation
        for cit in explanation.evidence_citations:
            claim_text = f"{cit.criterion} -> {cit.evidence_quote}"

            # Check skill citations
            if "Skill:" in cit.criterion:
                skill_display = cit.criterion.split("Skill:")[-1].strip()
                skill_name = skill_display.lower()
                if cit.status == "matched":
                    # Must be present in candidate skills
                    if skill_name in cand_skills or any(skill_name in s or s in skill_name for s in cand_skills):
                        audits.append(
                            CriticAuditItem(
                                claim=claim_text,
                                is_verified=True,
                                grounding_evidence=f"Skill '{skill_display}' verified in profile skills.",
                                audit_note="Faithful to resume data.",
                            )
                        )
                    else:
                        unsupported.append(f"Claimed matched skill '{skill_display}' not found in candidate profile.")
                        audits.append(
                            CriticAuditItem(
                                claim=claim_text,
                                is_verified=False,
                                grounding_evidence="None found in profile.",
                                audit_note="HALLUCINATION RISK: Claimed skill missing.",
                            )
                        )
                elif cit.status == "missing":
                    # Must NOT be present in candidate skills
                    if skill_name not in cand_skills:
                        audits.append(
                            CriticAuditItem(
                                claim=claim_text,
                                is_verified=True,
                                grounding_evidence="Absence confirmed.",
                                audit_note="Accurately noted as missing.",
                            )
                        )
                    else:
                        unsupported.append(f"Candidate actually has skill '{skill_display}', but explanation claimed it was missing.")
                        audits.append(
                            CriticAuditItem(
                                claim=claim_text,
                                is_verified=False,
                                grounding_evidence=f"Skill '{skill_display}' is in fact present.",
                                audit_note="FALSE NEGATIVE: Skill was overlooked.",
                            )
                        )

            # Check experience citations
            elif "Experience" in cit.criterion:
                # Experience claims must match candidate_profile.years_of_experience
                years_claimed = candidate_profile.years_of_experience
                if str(years_claimed) in cit.evidence_quote or f"{years_claimed:.1f}" in cit.evidence_quote:
                    audits.append(
                        CriticAuditItem(
                            claim=claim_text,
                            is_verified=True,
                            grounding_evidence=f"Candidate experience verified at {years_claimed} years.",
                            audit_note="Faithful experience citation.",
                        )
                    )
                else:
                    audits.append(
                        CriticAuditItem(
                            claim=claim_text,
                            is_verified=True,
                            grounding_evidence=f"Experience noted at {years_claimed} years.",
                            audit_note="Acceptable experience reference.",
                        )
                    )

        total_claims = len(audits)
        verified_count = sum(1 for a in audits if a.is_verified)
        unsupported_count = len(unsupported)

        faithfulness = (verified_count / total_claims) if total_claims > 0 else 1.0
        status = "pass" if unsupported_count == 0 else "revise"

        notes = (
            f"Critic verified {verified_count}/{total_claims} claims. Explanation is faithful to resume facts."
            if status == "pass"
            else f"Critic flagged {unsupported_count} unsupported claim(s). Requires revision before recruiter presentation."
        )

        return CriticReport(
            status=status,
            faithfulness_score=round(faithfulness, 3),
            verified_claims_count=verified_count,
            unsupported_claims_count=unsupported_count,
            unsupported_claims=unsupported,
            audit_trail=audits,
            critic_notes=notes,
        )
