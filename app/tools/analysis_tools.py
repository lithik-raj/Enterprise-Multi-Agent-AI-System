"""
Analysis Tools.

Exposes the NLP and ML services as structured tools for the multi-agent system.
Provides both legacy JSON-string helper functions and typed Pydantic models.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.services.nlp_service import get_nlp_service
from app.services.ml_service import get_ml_service

logger = logging.getLogger(__name__)


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class SkillExtractionInput(BaseModel):
    text: str = Field(..., description="Text content to extract skills from (resume or job description)")


class SkillExtractionOutput(BaseModel):
    extracted_skills: List[str]
    count: int
    entities: Dict[str, List[str]] = Field(default_factory=dict)


class ReportInput(BaseModel):
    company_name: str
    target_role: str
    matched_skills: List[str]
    missing_skills: List[str]
    compatibility_score: float
    learning_order: List[str]
    project_proposal: str


class ReportOutput(BaseModel):
    report_markdown: str
    summary: str


# ── Pydantic-based Tool Functions ─────────────────────────────────────────────

def extract_skills(input_data: SkillExtractionInput) -> SkillExtractionOutput:
    """
    Extract canonical skills and named entities from text using spaCy ontology.
    """
    logger.info("Executing extract_skills tool")
    nlp = get_nlp_service()
    skills = nlp.extract_skills(input_data.text)
    entities = nlp.extract_entities(input_data.text)
    return SkillExtractionOutput(
        extracted_skills=skills,
        count=len(skills),
        entities=entities,
    )


def generate_report(input_data: ReportInput) -> ReportOutput:
    """
    Format and structure the final enterprise assessment report.
    """
    logger.info("Executing generate_report tool for role '%s' at '%s'", input_data.target_role, input_data.company_name)
    strong_list = "\n".join(f"* {s}" for s in input_data.matched_skills) if input_data.matched_skills else "* Core foundations"
    needs_list = "\n".join(f"* {s}" for s in input_data.missing_skills) if input_data.missing_skills else "* None (Excellent match)"
    learning_list = "\n".join(f"{i+1}. {item}" for i, item in enumerate(input_data.learning_order))

    md = (
        f"### Enterprise AI Candidate & Role Assessment\n\n"
        f"**Target Role:** {input_data.target_role}\n"
        f"**Company:** {input_data.company_name}\n"
        f"**Automated Compatibility Score:** **{input_data.compatibility_score:.1f}%**\n\n"
        f"#### CURRENT MATCH\n\n"
        f"**Strong:**\n{strong_list}\n\n"
        f"**Needs improvement:**\n{needs_list}\n\n"
        f"#### RECOMMENDED LEARNING ORDER:\n\n"
        f"{learning_list}\n\n"
        f"#### RECOMMENDED PORTFOLIO PROJECT:\n\n"
        f"{input_data.project_proposal}\n"
    )

    summary = (
        f"Assessed match for {input_data.target_role} at {input_data.company_name}: "
        f"{input_data.compatibility_score:.1f}% match with {len(input_data.matched_skills)} matched skills and "
        f"{len(input_data.missing_skills)} skill gaps."
    )

    return ReportOutput(report_markdown=md, summary=summary)


# ── Legacy Functions (preserved for backward compatibility) ───────────────────

def extract_skills_tool(text: str) -> str:
    """
    Extract canonical AI/ML skills from a given text.
    
    Args:
        text: The text to analyze (e.g., resume or job description).
        
    Returns:
        A JSON string containing the list of skills found.
    """
    try:
        nlp = get_nlp_service()
        skills = nlp.extract_skills(text)
        return json.dumps({"extracted_skills": skills})
    except Exception as e:
        return json.dumps({"error": str(e)})


def calculate_compatibility_tool(
    resume_text: str,
    job_text: str,
    required_skills: List[str] = None,
    present_skills: List[str] = None,
) -> str:
    """
    Calculate semantic match and skill overlap between two texts.
    
    Args:
        resume_text: The full text of the resume.
        job_text: The full text of the job description.
        required_skills: Required skills extracted from the job (optional).
        present_skills: Skills possessed by the candidate (optional).
        
    Returns:
        A JSON string containing TF-IDF text similarity, skill overlap score, and overall match score.
    """
    try:
        ml = get_ml_service()
        
        sim_score = ml.calculate_text_similarity(resume_text, job_text)
        
        overlap_score = 0.0
        missing = []
        matched = []
        
        # If skills weren't provided, extract them on the fly
        if required_skills is None or present_skills is None:
            nlp = get_nlp_service()
            if required_skills is None:
                required_skills = nlp.extract_skills(job_text)
            if present_skills is None:
                present_skills = nlp.extract_skills(resume_text)
                
        overlap_result = ml.calculate_skill_overlap(present_skills, required_skills)
        overlap_score = overlap_result.get("overlap_score", 0.0)
        missing = overlap_result.get("missing_skills", [])
        matched = overlap_result.get("matched_skills", [])
        
        overall = ml.calculate_overall_compatibility(
            text_sim_score=sim_score,
            skill_overlap_score=overlap_score,
            weight_skills=0.6,
        )
        
        return json.dumps({
            "semantic_similarity": sim_score,
            "skill_overlap_score": overlap_score,
            "overall_compatibility_score": overall,
            "matched_skills": matched,
            "missing_skills": missing,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})
