"""
agents/job_analyzer_agent.py

Job Analyzer Agent: Ingests raw job descriptions and parses them into structured requirements:
  - Must-have skills (50% default weight)
  - Nice-to-have skills (10% default weight)
  - Minimum years of experience (25% default weight)
  - Semantic fit expectations (15% default weight)
  - Seniority level
  - Work authorization constraints
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ScoringWeights(BaseModel):
    must_have: float = Field(0.50, ge=0.0, le=1.0)
    experience: float = Field(0.25, ge=0.0, le=1.0)
    semantic: float = Field(0.15, ge=0.0, le=1.0)
    nice_to_have: float = Field(0.10, ge=0.0, le=1.0)


class JobRequirements(BaseModel):
    title: str = Field(..., description="Standardized job title")
    seniority: str = Field("Mid", description="Junior, Mid, Senior, Lead, Executive")
    min_years_experience: float = Field(0.0, ge=0.0)
    must_have_skills: List[str] = Field(default_factory=list)
    nice_to_have_skills: List[str] = Field(default_factory=list)
    required_work_authorization: Optional[str] = None
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    summary: str = Field(...)


class JobAnalyzerAgent:
    """Specialist agent analyzing job postings."""

    COMMON_SKILLS = [
        "python", "fastapi", "django", "flask", "langgraph", "langchain", "postgresql",
        "sql", "nosql", "mongodb", "redis", "docker", "kubernetes", "aws", "azure", "gcp",
        "react", "typescript", "javascript", "html", "css", "tailwind", "node.js",
        "machine learning", "deep learning", "nlp", "llm", "rag", "pytorch", "tensorflow",
        "scikit-learn", "data science", "pandas", "numpy", "git", "ci/cd", "rest api",
        "microservices", "graphql", "devops", "linux", "c++", "java", "go", "rust",
    ]

    def analyze(self, job_title: str, job_description: str, custom_weights: Optional[Dict[str, float]] = None) -> JobRequirements:
        """Analyze job description into structured requirements."""
        lower_desc = job_description.lower()

        # Seniority extraction
        seniority = "Mid"
        if any(w in lower_desc or w in job_title.lower() for w in ["lead", "principal", "staff"]):
            seniority = "Lead"
        elif any(w in lower_desc or w in job_title.lower() for w in ["senior", "sr."]):
            seniority = "Senior"
        elif any(w in lower_desc or w in job_title.lower() for w in ["junior", "entry", "jr.", "intern"]):
            seniority = "Junior"

        # Experience extraction
        exp_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+(?:professional|relevant|industry))?\s+experience", lower_desc)
        min_years = float(exp_match.group(1)) if exp_match else (5.0 if seniority == "Senior" else 2.0)

        # Must-have vs nice-to-have skill partitioning
        detected_skills = []
        for skill in self.COMMON_SKILLS:
            if re.search(rf"\b{re.escape(skill)}\b", lower_desc):
                detected_skills.append(skill.title() if len(skill) > 3 else skill.upper())

        # If sections exist, partition them
        must_haves = []
        nice_to_haves = []

        must_match = re.search(r"(?:requirements|qualifications|must[- ]have|what you'?ll need)[:\s]+(.*?)(?:nice[- ]to[- ]have|bonus|preferred|$)", lower_desc, re.DOTALL)
        if must_match:
            must_text = must_match.group(1)
            for s in detected_skills:
                if s.lower() in must_text:
                    must_haves.append(s)
                else:
                    nice_to_haves.append(s)
        else:
            # Default split: first 60% must have, rest nice to have
            split_idx = max(1, int(len(detected_skills) * 0.6))
            must_haves = detected_skills[:split_idx]
            nice_to_haves = detected_skills[split_idx:]

        if not must_haves and detected_skills:
            must_haves = detected_skills

        # Weights
        weights = ScoringWeights(**custom_weights) if custom_weights else ScoringWeights()

        return JobRequirements(
            title=job_title,
            seniority=seniority,
            min_years_experience=min_years,
            must_have_skills=sorted(list(set(must_haves))),
            nice_to_have_skills=sorted(list(set(nice_to_haves))),
            required_work_authorization="US Citizen / Permanent Resident" if "citizen" in lower_desc or "clearance" in lower_desc else None,
            weights=weights,
            summary=f"{seniority} level opening requiring {min_years}+ years experience and expertise in {', '.join(must_haves[:3])}.",
        )
