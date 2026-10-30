"""
ATS Resume & Score Analyzer Service.

Provides deep Applicant Tracking System (ATS) parsing, heuristic scoring,
keyword gap analysis, action verb detection, and actionable formatting audits.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Strong ATS Action Verbs ──────────────────────────────────────────────────
STRONG_ACTION_VERBS = {
    "architected", "engineered", "developed", "designed", "implemented", "deployed",
    "optimized", "scaled", "spearheaded", "accelerated", "reduced", "increased",
    "built", "orchestrated", "automated", "trained", "fine-tuned", "evaluated",
    "benchmarked", "integrated", "streamlined", "transformed", "modeled",
    "programmed", "formulated", "established", "supervised", "mentored", "delivered"
}

# ── Target Role Skill Benchmarks ─────────────────────────────────────────────
ROLE_BENCHMARKS = {
    "ai_ml": {
        "title": "AI / Machine Learning Engineer",
        "core_skills": [
            "python", "machine learning", "deep learning", "pytorch", "tensorflow",
            "scikit-learn", "nlp", "rag", "langgraph", "vector databases", "faiss",
            "fastapi", "docker", "sql", "git", "transformers", "pandas", "numpy"
        ],
        "keywords": ["model evaluation", "embeddings", "rest api", "pipeline", "fine-tuning"]
    },
    "software_engineer": {
        "title": "Software Development Engineer (SDE)",
        "core_skills": [
            "python", "java", "c++", "data structures", "algorithms", "sql",
            "fastapi", "spring boot", "react", "docker", "git", "linux",
            "microservices", "rest api", "system design", "object oriented"
        ],
        "keywords": ["scalability", "unit testing", "ci/cd", "concurrency", "design patterns"]
    },
    "data_scientist": {
        "title": "Data Scientist / Analytics Engineer",
        "core_skills": [
            "python", "sql", "pandas", "numpy", "scikit-learn", "data visualization",
            "statistics", "tableau", "power bi", "machine learning", "git", "spark"
        ],
        "keywords": ["a/b testing", "hypothesis testing", "etl", "predictive modeling"]
    }
}


class ATSCategoryScore(BaseModel):
    category: str
    score: float
    max_score: float
    percentage: float
    feedback: str


class ATSAnalysisResult(BaseModel):
    overall_score: int
    score_grade: str  # Excellent (85-100), Good (70-84), Needs Improvement (50-69), Critical (0-49)
    target_role: str
    word_count: int
    readability_level: str
    contact_info: Dict[str, bool]
    sections_detected: List[str]
    sections_missing: List[str]
    action_verbs_found: List[str]
    action_verb_count: int
    quantifiable_metrics_count: int
    metric_snippets: List[str]
    matched_skills: List[str]
    missing_skills: List[str]
    category_scores: List[ATSCategoryScore]
    critical_fixes: List[str]
    improvements: List[str]
    strengths: List[str]


class ATSService:
    """Production ATS Resume Scorer and Formatter."""

    def __init__(self):
        pass

    def analyze(self, resume_text: str, target_role_key: Optional[str] = "ai_ml") -> ATSAnalysisResult:
        text = resume_text or ""
        text_lower = text.lower()
        words = re.findall(r"\b[a-zA-Z0-9_\-+#.]+\b", text)
        word_count = len(words)

        # 1. Contact Information Detection
        has_email = bool(re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))
        has_phone = bool(re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text))
        has_linkedin = bool(re.search(r"linkedin\.com/in/[a-zA-Z0-9_-]+", text_lower))
        has_github = bool(re.search(r"github\.com/[a-zA-Z0-9_-]+", text_lower))
        has_portfolio = bool(re.search(r"(portfolio|website|https?://[^\s]+)", text_lower))
        has_location = bool(re.search(r"\b(bengaluru|bangalore|hyderabad|pune|mumbai|delhi|gurugram|chennai|noida|san francisco|california|new york|remote)\b", text_lower))

        contact_info = {
            "email": has_email,
            "phone": has_phone,
            "linkedin": has_linkedin,
            "github": has_github,
            "location": has_location,
        }

        contact_score_val = (
            (4.0 if has_email else 0.0) +
            (3.0 if has_phone else 0.0) +
            (3.0 if has_linkedin else 0.0) +
            (3.0 if has_github else 0.0) +
            (2.0 if has_location else 0.0)
        )

        # 2. Section Structure Detection
        standard_sections = {
            "Summary / Objective": [r"summary", r"objective", r"profile", r"about me"],
            "Experience / Internships": [r"experience", r"employment", r"work history", r"internships", r"experience:"],
            "Technical Skills": [r"skills", r"technical skills", r"competencies", r"technologies", r"tools"],
            "Education": [r"education", r"academic", r"qualifications", r"degree", r"university", r"college"],
            "Projects": [r"projects", r"academic projects", r"key projects", r"personal projects"],
            "Certifications / Awards": [r"certifications", r"awards", r"achievements", r"licenses", r"publications"],
        }

        detected_sections = []
        missing_sections = []

        for sec_name, patterns in standard_sections.items():
            matched = any(re.search(r"(?i)\b" + p + r"\b", text) for p in patterns)
            if matched:
                detected_sections.append(sec_name)
            else:
                missing_sections.append(sec_name)

        structure_score_val = (len(detected_sections) / len(standard_sections)) * 20.0

        # 3. Action Verbs Analysis
        found_verbs = set()
        for word in words:
            w_low = word.lower()
            if w_low in STRONG_ACTION_VERBS:
                found_verbs.add(w_low)

        action_verb_count = len(found_verbs)
        action_verb_score_val = min(20.0, action_verb_count * 2.5)

        # 4. Quantifiable Metrics & Numerical Impact
        # Patterns for: 34%, $20k, 100ms, 50K+, 2x, etc.
        metric_matches = re.findall(
            r"(\b\d+(?:\.\d+)?%\b|\b\d+\s*x\b|\$\s*\d+[\d,]*(?:\.\d+)?(?:\s*[kmbt])?|\b\d+\+?\s*(?:k|m|million|users|requests|rps|ms|fps|gb|tb|tbps|sec|seconds)\b|\b(?:reduced|increased|improved|cut|boosted|saved)\s+by\s+\d+%)",
            text,
            flags=re.IGNORECASE
        )
        metric_snippets = list(set([m.strip() for m in metric_matches if len(m.strip()) > 1]))[:6]
        quantifiable_count = len(metric_matches)
        metrics_score_val = min(20.0, quantifiable_count * 4.0)

        # 5. Technical Skill Matching & Unified Calibration
        from app.services.scoring_engine import get_unified_scoring_engine
        scoring_engine = get_unified_scoring_engine()
        calibrated_eval = scoring_engine.evaluate_candidate(
            resume_text=text,
            target_role=target_role_key or "ai_ml",
        )

        matched_skills = calibrated_eval["matched_skills"]
        missing_skills = calibrated_eval["missing_skills"]
        skills_score_val = (calibrated_eval["score"] / 100.0) * 25.0

        # 6. Readability & Formatting (max 10 points)
        formatting_score_val = 10.0
        if word_count < 200:
            formatting_score_val -= 5.0
        elif word_count > 1500:
            formatting_score_val -= 3.0

        has_bullet_points = bool(re.search(r"(\n\s*[-*•–]\s+|\n\s*\d+\.\s+)", text))
        if not has_bullet_points and word_count > 100:
            formatting_score_val -= 3.0

        formatting_score_val = max(2.0, formatting_score_val)

        # 7. Overall Aggregate Score (0 - 100)
        # Harmonized with Batch and Recruiter Match Score
        ats_audit_score = int(round(
            contact_score_val +
            structure_score_val +
            action_verb_score_val +
            metrics_score_val +
            skills_score_val
        ))

        # Calibrated blend: 75% core competency match from calibrated engine + 25% ATS formatting
        blended_score = int(round((0.75 * calibrated_eval["score"]) + (0.25 * ats_audit_score)))
        total_score = max(10, min(99, blended_score))

        # Determine Grade
        if total_score >= 85:
            grade = "Excellent (ATS Ready)"
        elif total_score >= 70:
            grade = "Good (Competitive)"
        elif total_score >= 50:
            grade = "Needs Improvement"
        else:
            grade = "Critical Fixes Required"

        # 8. Category Breakdown
        categories = [
            ATSCategoryScore(
                category="Contact Information & Links",
                score=round(contact_score_val, 1),
                max_score=15.0,
                percentage=round((contact_score_val / 15.0) * 100),
                feedback="All essential contact handles present" if contact_score_val >= 12 else "Missing LinkedIn, GitHub, or direct contact links"
            ),
            ATSCategoryScore(
                category="Section Structure & Hierarchy",
                score=round(structure_score_val, 1),
                max_score=20.0,
                percentage=round((structure_score_val / 20.0) * 100),
                feedback=f"{len(detected_sections)} of {len(standard_sections)} standard ATS sections identified"
            ),
            ATSCategoryScore(
                category="Action Verbs & Leadership",
                score=round(action_verb_score_val, 1),
                max_score=20.0,
                percentage=round((action_verb_score_val / 20.0) * 100),
                feedback=f"Found {action_verb_count} distinct high-impact action verbs"
            ),
            ATSCategoryScore(
                category="Quantifiable Metrics & Impact",
                score=round(metrics_score_val, 1),
                max_score=20.0,
                percentage=round((metrics_score_val / 20.0) * 100),
                feedback=f"Detected {quantifiable_count} measurable impact metrics (%, scale, latency)"
            ),
            ATSCategoryScore(
                category=f"Core Skills ({calibrated_eval.get('target_role', 'Target Role')})",
                score=round(skills_score_val, 1),
                max_score=25.0,
                percentage=round((skills_score_val / 25.0) * 100),
                feedback=f"Matched {len(matched_skills)} core technical skills ({len(missing_skills)} missing)"
            ),
        ]

        # 9. Actionable Fixes & Insights
        critical_fixes = []
        improvements = []
        strengths = []

        if not has_email:
            critical_fixes.append("Add a professional email address at the very top of your resume.")
        if not has_phone:
            critical_fixes.append("Add a direct phone number with country/area code.")
        if not has_github and target_role_key in ["ai_ml", "software_engineer"]:
            critical_fixes.append("Add a clickable GitHub profile link showcasing your open-source projects.")
        if "Experience / Internships" in missing_sections and "Projects" in missing_sections:
            critical_fixes.append("Missing both Experience and Projects sections. ATS requires at least one of these to parse candidate achievements.")

        if quantifiable_count < 3:
            improvements.append("Quantify your achievements! Add 3+ metrics using numbers (e.g. 'Improved inference throughput by 35%', 'Handled 5,000+ daily requests').")
        if action_verb_count < 5:
            improvements.append(f"Replace passive phrasing with strong action verbs (e.g. 'Architected', 'Spearheaded', 'Optimized', 'Deployed').")
        if target_role_key in ROLE_BENCHMARKS:
            target_role_title = ROLE_BENCHMARKS[target_role_key]["title"]
        else:
            target_role_title = calibrated_eval.get("target_role") or "AI / Machine Learning Engineer"
        if len(missing_skills) > 4:
            top_miss = missing_skills[:4]
            improvements.append(f"Add high-frequency keyword skills for {target_role_title}: {', '.join(top_miss)}.")
        if word_count < 300:
            improvements.append("Your resume content is relatively brief (< 300 words). Expand on project architecture, technical stack, and results.")

        if has_linkedin:
            strengths.append("LinkedIn profile is present and easily discoverable by recruiters.")
        if action_verb_count >= 5:
            strengths.append(f"Great use of energetic action verbs ({', '.join(list(found_verbs)[:4])}).")
        if len(matched_skills) >= 6:
            strengths.append(f"Strong technical alignment with {target_role_title} ({', '.join(matched_skills[:5])}).")
        if has_bullet_points:
            strengths.append("Standard bullet point formatting facilitates clean parsing by automated ATS engines.")

        return ATSAnalysisResult(
            overall_score=total_score,
            score_grade=grade,
            target_role=target_role_title,
            word_count=word_count,
            readability_level="High (Clean Standard Text)" if formatting_score_val >= 8 else "Moderate",
            contact_info=contact_info,
            sections_detected=detected_sections,
            sections_missing=missing_sections,
            action_verbs_found=list(found_verbs)[:12],
            action_verb_count=action_verb_count,
            quantifiable_metrics_count=quantifiable_count,
            metric_snippets=metric_snippets,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            category_scores=categories,
            critical_fixes=critical_fixes,
            improvements=improvements,
            strengths=strengths,
        )


_ats_service = None

def get_ats_service() -> ATSService:
    global _ats_service
    if _ats_service is None:
        _ats_service = ATSService()
    return _ats_service
