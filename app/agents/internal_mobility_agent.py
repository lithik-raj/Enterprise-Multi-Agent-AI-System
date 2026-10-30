"""
agents/internal_mobility_agent.py

Internal Mobility Agent: Identifies internal employees qualified for lateral moves
or promotions into newly opened job requisitions.
Recommends targeted upskilling pathways to bridge minor skill gaps.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.agents.job_analyzer_agent import JobRequirements

logger = logging.getLogger(__name__)


class InternalEmployee(BaseModel):
    employee_id: str
    name: str
    current_role: str
    department: str
    tenure_years: float
    skills: List[str]
    performance_rating: float = Field(..., ge=1.0, le=5.0)


class InternalMobilityMatch(BaseModel):
    employee_id: str
    employee_name: str
    current_role: str
    suitability_score: float = Field(..., ge=0.0, le=100.0)
    readiness_level: str = Field(..., description="'Immediate Transition', 'Promotable (1-3 mos)', 'Upskill Candidate'")
    matched_competencies: List[str]
    suggested_upskilling: List[str]
    rationale: str


class InternalMobilityAgent:
    """Specialist agent matching internal talent to open job openings."""

    def evaluate_internal_talent(
        self,
        employees: List[InternalEmployee],
        job: JobRequirements,
    ) -> List[InternalMobilityMatch]:
        """Matches a pool of internal employees against an open job opening."""
        matches: List[InternalMobilityMatch] = []
        req_skills = set(s.lower() for s in job.must_have_skills)

        for emp in employees:
            emp_skills = set(s.lower() for s in emp.skills)
            overlap = req_skills.intersection(emp_skills)
            missing = req_skills.difference(emp_skills)

            skill_ratio = len(overlap) / len(req_skills) if req_skills else 1.0

            # Composite score (60% skill match, 25% tenure, 15% performance)
            perf_norm = (emp.performance_rating / 5.0)
            tenure_score = min(1.0, emp.tenure_years / max(1.0, job.min_years_experience))

            raw_score = (0.60 * skill_ratio + 0.25 * tenure_score + 0.15 * perf_norm) * 100.0

            if raw_score >= 80.0:
                readiness = "Immediate Transition"
            elif raw_score >= 60.0:
                readiness = "Promotable (1-3 mos)"
            else:
                readiness = "Upskill Candidate"

            matches.append(
                InternalMobilityMatch(
                    employee_id=emp.employee_id,
                    employee_name=emp.name,
                    current_role=emp.current_role,
                    suitability_score=round(raw_score, 1),
                    readiness_level=readiness,
                    matched_competencies=[s.title() for s in overlap],
                    suggested_upskilling=[s.title() for s in missing],
                    rationale=(
                        f"Employee possesses {len(overlap)} of {len(req_skills)} required core skills with a "
                        f"{emp.performance_rating}/5.0 performance rating over {emp.tenure_years} years tenure."
                    ),
                )
            )

        # Sort highest suitability first
        matches.sort(key=lambda m: m.suitability_score, reverse=True)
        return matches
