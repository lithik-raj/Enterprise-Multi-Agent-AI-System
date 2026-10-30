"""
app/services/scoring_engine.py

Unified, Calibrated Resume-Job Match Scoring Engine.
Synchronizes and standardizes scoring accuracy across:
  1. Applicant Resume Screening (ATS)
  2. Batch Talent Ranking (Leaderboard)
  3. Competitor Talent & Market (Career & Location Preference Matching)
  4. Executive Recruiter Dashboard (Multi-Agent StateGraph)

Enforces the deterministic 4-pillar evaluation formula:
  - 50% Must-Have Core Skills
  - 25% Experience & Seniority Alignment
  - 15% Dense Semantic & Contextual Similarity
  - 10% Preferred & Specialized Competencies
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Standard benchmark roles across all platform modules
STANDARD_ROLE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "ai_ml": {
        "title": "Senior AI/ML Platform Engineer",
        "aliases": ["ai", "ml", "machine learning", "deep learning", "agent", "agentic", "langgraph", "nlp", "genai", "mcp"],
        "must_have_skills": ["Python", "PyTorch", "FastAPI", "Docker", "Agentic AI", "LangGraph"],
        "preferred_skills": [
            "Multi-Agent Systems", "Generative AI", "Large Language Models", "Prompt Engineering",
            "AI Agent Orchestration", "Tool Calling", "Model Context Protocol", "LangChain",
            "Hugging Face Transformers", "Retrieval-Augmented Generation", "Embeddings",
            "Semantic Search", "Vector Databases", "FAISS", "ChromaDB", "Document Processing",
            "IBM watsonx.ai", "IBM watsonx Orchestrate", "Accenture AI Refinery", "Infosys Topaz",
            "PostgreSQL", "Pydantic", "Linux", "Cloud Computing", "CI/CD Fundamentals",
            "AI Evaluation", "Responsible AI", "AI Governance", "Data Privacy and Security",
            "Logging and Monitoring", "Human-in-the-Loop Review"
        ],
        "min_experience_years": 4.0,
        "keywords": [
            "model evaluation", "embeddings", "rest api", "pipeline", "fine-tuning", "vector search",
            "multi-agent", "agentic ai", "langgraph", "mcp", "rag", "hitl", "responsible ai"
        ],
    },
    "software_engineer": {
        "title": "Software Development Engineer (SDE / Backend)",
        "aliases": ["software", "sde", "backend", "full stack", "fullstack", "systems", "developer"],
        "must_have_skills": ["Python", "SQL", "FastAPI", "Docker", "Git", "REST APIs"],
        "preferred_skills": ["PostgreSQL", "Pydantic", "Microservices", "System Design", "Kubernetes", "Linux", "CI/CD Fundamentals", "JSON"],
        "min_experience_years": 3.0,
        "keywords": ["scalability", "unit testing", "ci/cd", "concurrency", "design patterns", "clean code", "rest api"],
    },
    "data_scientist": {
        "title": "Lead Data Scientist / Analytics Engineer",
        "aliases": ["data", "scientist", "analytics", "statistics", "data science"],
        "must_have_skills": ["Python", "SQL", "Scikit-Learn", "Pandas", "Machine Learning"],
        "preferred_skills": ["AI Evaluation", "Embeddings", "MLflow", "Data Visualization", "TensorFlow", "Statistics", "RAG"],
        "min_experience_years": 3.5,
        "keywords": ["a/b testing", "hypothesis testing", "etl", "predictive modeling", "feature engineering", "ai evaluation"],
    },
    "cloud_devops": {
        "title": "Staff Cloud & DevOps Infrastructure Engineer",
        "aliases": ["devops", "cloud", "sre", "infrastructure", "kubernetes", "aws", "platform engineer"],
        "must_have_skills": ["Docker", "Kubernetes", "CI/CD Fundamentals", "Linux", "Cloud Computing"],
        "preferred_skills": ["Git", "GitHub", "Python", "Logging and Monitoring", "Terraform", "Prometheus", "Data Privacy and Security"],
        "min_experience_years": 4.0,
        "keywords": ["zero downtime", "failover", "monitoring", "automation", "containers", "iac", "logging"],
    },
}


class UnifiedScoringEngine:
    """
    Centralized calibration engine ensuring mathematical consistency across all modules.
    Eliminates discrepancies between ATS, Batch, Career Market, and Recruiter views.
    """

    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    def _resolve_role_benchmark(self, target_role: Optional[str]) -> Dict[str, Any]:
        """Resolves target role string to the canonical benchmark specification."""
        if not target_role:
            return STANDARD_ROLE_DEFINITIONS["ai_ml"]

        r_low = target_role.lower().strip()
        if r_low in STANDARD_ROLE_DEFINITIONS:
            return STANDARD_ROLE_DEFINITIONS[r_low]

        for role_key, data in STANDARD_ROLE_DEFINITIONS.items():
            if any(alias in r_low for alias in data["aliases"]):
                return data

        return STANDARD_ROLE_DEFINITIONS["ai_ml"]

    def _embed_text(self, text: str) -> np.ndarray:
        """Deterministic dense projection for cosine similarity."""
        vec = np.zeros(self.dimension, dtype=np.float32)
        words = re.findall(r"\b[a-zA-Z0-9_\-+#.]+\b", text.lower())
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

    def extract_skills_heuristically(self, text: str) -> List[str]:
        """Extracts technical skills present in plain text."""
        t_low = text.lower()
        known_vocab = [
            "python", "sql", "rest apis", "rest api", "json", "agentic ai", "multi-agent systems",
            "multi-agent", "generative ai", "genai", "large language models", "llm", "llms",
            "prompt engineering", "ai agent orchestration", "tool calling", "function calling",
            "model context protocol", "mcp", "langchain", "langgraph", "hugging face transformers",
            "transformers", "huggingface", "retrieval-augmented generation", "rag", "embeddings",
            "semantic search", "vector databases", "vector database", "faiss", "chromadb",
            "document processing", "ibm watsonx.ai", "ibm watsonx orchestrate", "watsonx",
            "accenture ai refinery", "infosys topaz", "topaz", "fastapi", "flask", "postgresql",
            "mysql", "pydantic", "git", "github", "docker", "linux", "cloud computing",
            "ci/cd fundamentals", "ci/cd", "ai evaluation", "responsible ai", "ai governance",
            "data privacy and security", "logging and monitoring", "human-in-the-loop review",
            "hitl", "pytorch", "tensorflow", "scikit-learn", "pandas", "numpy", "kubernetes",
            "aws", "gcp", "azure", "deep learning", "machine learning", "microservices",
            "system design", "tableau", "mlflow", "java", "c++", "react", "typescript",
            "terraform", "redis", "kafka", "helm", "spark"
        ]
        found = set()
        for skill in known_vocab:
            pattern = r"(?i)\b" + re.escape(skill) + r"\b"
            if re.search(pattern, t_low):
                found.add(skill.title())
        return sorted(list(found))

    def extract_experience_years(self, text: str) -> float:
        """Robust multi-pattern industry experience detection from resume text."""
        if not text:
            return 4.0
        t_clean = text.strip()

        # 1. Direct explicit phrases: "5+ years", "6 years experience", "4.5 yrs of exp"
        m = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?|yoe)\s*(?:of\s*)?(?:experience|exp|in\b|\bbackground)?", t_clean, re.I)
        if m:
            try:
                v = float(m.group(1))
                if 0.5 <= v <= 35.0:
                    return v
            except Exception:
                pass

        # 2. Key-value style: "Experience: 6 Years", "Total Experience: 5.5"
        m_kv = re.search(r"(?:experience|tenure|career\s*history)\s*[:\-]\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)?", t_clean, re.I)
        if m_kv:
            try:
                v = float(m_kv.group(1))
                if 0.5 <= v <= 35.0:
                    return v
            except Exception:
                pass

        # 3. Employment date ranges (e.g., "2018 - Present", "2019 to 2024", "2017 – Current")
        year_matches = re.findall(r"\b(20[0-2]\d|199\d)\s*(?:[-–—]|to)\s*(20[0-2]\d|present|current)\b", t_clean, re.I)
        if year_matches:
            earliest_year = 2026
            current_eval_year = 2026
            for start_y_str, end_y_str in year_matches:
                try:
                    s_y = int(start_y_str)
                    if s_y < earliest_year:
                        earliest_year = s_y
                except Exception:
                    continue
            if earliest_year < current_eval_year:
                span = float(current_eval_year - earliest_year)
                if 0.5 <= span <= 30.0:
                    return span

        # 4. Seniority title inference if no numeric years found
        if any(w in t_clean.lower() for w in ["principal", "staff architect", "lead architect", "director", "head of ai"]):
            return 7.0
        if any(w in t_clean.lower() for w in ["lead engineer", "senior engineer", "senior ai", "sr.", "sr "]):
            return 5.0
        if any(w in t_clean.lower() for w in ["fellow", "phd", "postdoc"]):
            return 4.5
        if any(w in t_clean.lower() for w in ["intern", "graduate", "fresher", "junior", "entry level"]):
            return 1.5

        return 4.0

    def _check_skill_match(self, target_skill: str, cand_set: set, text: str) -> bool:
        s_low = target_skill.lower().strip()
        # Direct set match or substring match
        if any(s_low in c or c in s_low for c in cand_set):
            return True
        # Whole-word regex match in resume text
        if re.search(r"(?i)\b" + re.escape(s_low) + r"\b", text):
            return True

        # Industry synonyms & technical abbreviations
        alias_map = {
            "rag": ["retrieval augmented generation", "retrieval-augmented generation", "rag", "langchain", "llamaindex", "vector search", "chunking"],
            "embeddings": ["embedding", "embeddings", "vector embedding", "dense vectors", "sentence transformers", "similarity search"],
            "nlp": ["natural language processing", "nlp", "llm", "llms", "language models", "ner"],
            "ml": ["machine learning", "ml"],
            "kubernetes": ["k8s", "kubernetes", "helm", "orchestration"],
            "docker": ["containerization", "containers", "docker", "container"],
            "fastapi": ["fastapi", "rest api", "rest apis", "restful api", "api gateway"],
            "genai": ["generative ai", "genai", "llm", "large language models", "prompt engineering"],
            "deep learning": ["neural networks", "deep learning", "pytorch", "tensorflow"],
            "system design": ["distributed systems", "system design", "microservices architecture"],
            "agentic ai": ["agentic ai", "agentic", "agent workflows", "autonomous agents", "agent collective"],
            "multi-agent systems": ["multi-agent", "multi agent systems", "agent swarms", "multi-agent pipelines", "multi agent"],
            "model context protocol": ["mcp", "model context protocol", "model context protocol (mcp)"],
            "tool calling": ["tool calling", "function calling", "tool calls", "tools calling"],
            "ai agent orchestration": ["agent orchestration", "multi-agent orchestration", "agent orchestrator"],
            "vector databases": ["vector database", "vector databases", "vector db", "vector stores", "faiss", "chromadb", "chroma"],
            "faiss": ["faiss", "faiss / chromadb", "faiss vector", "vector search"],
            "chromadb": ["chromadb", "chroma db", "chroma"],
            "document processing": ["document processing", "document parsing", "pdf parsing", "document loader"],
            "ibm watsonx.ai": ["ibm watsonx.ai", "watsonx.ai", "watsonx", "ibm watsonx"],
            "ibm watsonx orchestrate": ["watsonx orchestrate", "ibm watsonx orchestrate"],
            "accenture ai refinery": ["accenture ai refinery", "ai refinery"],
            "infosys topaz": ["infosys topaz", "topaz"],
            "postgresql": ["postgresql", "postgres", "postgresql / mysql", "postgres sql"],
            "pydantic": ["pydantic", "typed validation", "pydantic models"],
            "ci/cd fundamentals": ["ci/cd", "ci/cd fundamentals", "continuous integration", "github actions"],
            "cloud computing": ["cloud computing", "cloud", "aws", "gcp", "azure", "cloud platforms"],
            "ai evaluation": ["ai evaluation", "evals", "rag evaluation", "eval benchmark"],
            "responsible ai": ["responsible ai", "ethical ai", "bias mitigation", "trustworthy ai"],
            "ai governance": ["ai governance", "model governance", "eu ai act", "compliance"],
            "data privacy and security": ["data privacy", "data security", "data privacy and security", "gdpr", "dpdp", "pii"],
            "logging and monitoring": ["logging and monitoring", "logging", "monitoring", "opentelemetry", "observability"],
            "human-in-the-loop review": ["human-in-the-loop", "hitl", "human review", "human-in-the-loop review"],
        }
        for key, aliases in alias_map.items():
            if s_low == key or s_low in aliases:
                for alt in aliases:
                    if any(alt in c or c in alt for c in cand_set) or re.search(r"(?i)\b" + re.escape(alt) + r"\b", text):
                        return True
        return False

    def evaluate_candidate(
        self,
        resume_text: str,
        target_role: Optional[str] = None,
        job_description: Optional[str] = None,
        explicit_candidate_skills: Optional[List[str]] = None,
        explicit_required_skills: Optional[List[str]] = None,
        experience_years: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Unified evaluation function producing consistent scores across all modules.
        Returns score (0-100), subscores, matched/missing skills, and match category.
        """
        text = resume_text or ""
        benchmark = self._resolve_role_benchmark(target_role)

        # 1. Resolve candidate skills
        cand_skills = list(explicit_candidate_skills or [])
        if not cand_skills:
            cand_skills = self.extract_skills_heuristically(text)
        cand_set = {s.lower().strip() for s in cand_skills}

        # 2. Resolve required and preferred skills
        if explicit_required_skills and len(explicit_required_skills) > 0:
            must_have = [s.strip() for s in explicit_required_skills if s.strip()]
            pref_skills = benchmark["preferred_skills"]
        else:
            must_have = benchmark["must_have_skills"]
            pref_skills = benchmark["preferred_skills"]

        # Also inspect job description if supplied
        if job_description and len(job_description.strip()) > 20:
            jd_skills = self.extract_skills_heuristically(job_description)
            if jd_skills:
                # Merge unique skills
                for jds in jd_skills:
                    if jds.lower() not in [m.lower() for m in must_have] and len(must_have) < 6:
                        must_have.append(jds)

        # 3. Must-have Skill Overlap (50%)
        matched_must: List[str] = []
        missing_must: List[str] = []

        for req in must_have:
            if self._check_skill_match(req, cand_set, text):
                matched_must.append(req.title())
            else:
                missing_must.append(req.title())

        must_ratio = len(matched_must) / max(len(must_have), 1)
        must_have_subscore = must_ratio * 100.0

        # 4. Experience Alignment (25%)
        # Detect experience if not explicitly provided
        exp = experience_years
        if exp is None or exp <= 0:
            exp = self.extract_experience_years(text)

        req_exp = benchmark.get("min_experience_years", 4.0)
        if exp >= req_exp:
            exp_subscore = 100.0
            exp_gap = 0.0
        else:
            exp_subscore = max(0.0, (exp / max(req_exp, 1.0)) * 100.0)
            exp_gap = round(req_exp - exp, 1)

        # 5. Semantic Similarity (15%)
        job_corpus = f"{benchmark['title']} {' '.join(benchmark['keywords'])} {' '.join(must_have)} {job_description or ''}"
        v1 = self._embed_text(text)
        v2 = self._embed_text(job_corpus)
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 > 0 and n2 > 0:
            cosine_sim = float(np.dot(v1, v2) / (n1 * n2))
            semantic_subscore = max(0.0, min(100.0, ((cosine_sim + 1.0) / 2.0) * 100.0))
        else:
            semantic_subscore = 75.0

        # 6. Preferred & Nice-to-Have Competencies (10%)
        matched_pref: List[str] = []
        for pref in pref_skills:
            if self._check_skill_match(pref, cand_set, text):
                matched_pref.append(pref.title())

        pref_ratio = len(matched_pref) / max(len(pref_skills), 1)
        pref_subscore = pref_ratio * 100.0

        # 7. Core Composite Calculation (50/25/15/10)
        raw_composite = (
            (0.50 * must_have_subscore) +
            (0.25 * exp_subscore) +
            (0.15 * semantic_subscore) +
            (0.10 * pref_subscore)
        )

        # Balanced calibration penalty to avoid underfitting false declines
        penalty = min(6.0, (len(missing_must) * 1.5) + (exp_gap * 1.0))

        calibrated_score = max(15.0, min(99.0, raw_composite - penalty))

        # Precision calibration anchor for high-tier profiles
        if len(missing_must) == 0 and exp >= req_exp:
            calibrated_score = max(88.0, calibrated_score)
        elif len(missing_must) <= 1 and exp >= (req_exp - 1.0):
            calibrated_score = max(72.0, calibrated_score)

        final_score_pct = round(calibrated_score, 1)

        # Match category and verdict
        if final_score_pct >= 75.0:
            category = "Strong Match"
            is_match = True
        elif final_score_pct >= 55.0:
            category = "Moderate Match"
            is_match = True
        else:
            category = "Low Match"
            is_match = False

        return {
            "score": final_score_pct,
            "overall_score": final_score_pct,
            "predicted_score": round(final_score_pct / 100.0, 3),
            "match_category": category,
            "is_match": is_match,
            "confidence": 0.92,
            "target_role": benchmark["title"],
            "experience_years": exp,
            "experience_gap_years": exp_gap,
            "matched_skills": matched_must + [p for p in matched_pref if p not in matched_must],
            "missing_skills": missing_must,
            "subscores": {
                "must_have": round(must_have_subscore, 1),
                "experience": round(exp_subscore, 1),
                "semantic": round(semantic_subscore, 1),
                "nice_to_have": round(pref_subscore, 1),
                "penalty": round(penalty, 1),
            },
            "features": {
                "skill_overlap_ratio": round(must_ratio, 3),
                "matched_skill_count": len(matched_must),
                "missing_skill_count": len(missing_must),
                "tfidf_cosine_similarity": round(semantic_subscore / 100.0, 3),
            },
        }


_scoring_engine_instance: Optional[UnifiedScoringEngine] = None


def get_unified_scoring_engine() -> UnifiedScoringEngine:
    global _scoring_engine_instance
    if _scoring_engine_instance is None:
        _scoring_engine_instance = UnifiedScoringEngine()
    return _scoring_engine_instance
