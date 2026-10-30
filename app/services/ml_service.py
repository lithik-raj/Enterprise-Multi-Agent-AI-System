"""
Machine Learning Service.

Features:
- TF-IDF vectorization and cosine similarity
- Skill overlap calculation
- Match scoring based on similarity and overlap
- Uses Scikit-learn (traditional ML). Transformers are used in Phase 6 for RAG.
"""

import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

class MLService:
    def __init__(self):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            self.TfidfVectorizer = TfidfVectorizer
            self.cosine_similarity = cosine_similarity
            self.np = np
        except ImportError as exc:
            raise RuntimeError("scikit-learn or numpy is not installed. Run: pip install scikit-learn numpy") from exc
        
        # Instantiate a reusable vectorizer with english stop words
        self.vectorizer = self.TfidfVectorizer(stop_words="english")
        logger.info("MLService initialised with Scikit-learn TF-IDF")

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic compatibility between two text blocks (e.g. resume and job).
        Returns a float between 0.0 and 1.0.
        """
        if not text1 or not text2:
            return 0.0
            
        try:
            # Fit and transform the two texts
            tfidf_matrix = self.vectorizer.fit_transform([text1, text2])
            
            # Calculate cosine similarity between the first item (index 0) and second (index 1)
            sim_matrix = self.cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            
            # Extract scalar
            similarity_score = float(sim_matrix[0][0])
            
            # Clip between 0 and 1 just in case of float imprecision
            return max(0.0, min(1.0, similarity_score))
        except Exception as e:
            logger.error("Failed to calculate text similarity: %s", e)
            return 0.0

    def calculate_skill_overlap(self, resume_skills: list[str], job_skills: list[str]) -> dict[str, Any]:
        """
        Calculate overlap between present skills and required skills.
        Returns a structured dictionary with metrics.
        """
        req_set = set(job_skills)
        res_set = set(resume_skills)
        
        if not req_set:
            return {
                "overlap_score": 0.0,
                "matched_skills": [],
                "missing_skills": []
            }
            
        matched = req_set.intersection(res_set)
        missing = req_set.difference(res_set)
        
        overlap_score = len(matched) / len(req_set)
        
        return {
            "overlap_score": round(overlap_score, 3),
            "matched_skills": sorted(list(matched)),
            "missing_skills": sorted(list(missing))
        }
        
    def calculate_overall_compatibility(self, text_sim_score: float, skill_overlap_score: float, weight_skills: float = 0.6) -> float:
        """
        Calculate a final compatibility score by weighting TF-IDF similarity against hard skill overlap.
        Skill overlap forms the core requirement, while text sim acts as a cultural/soft-skill proxy.
        """
        if not (0.0 <= weight_skills <= 1.0):
            weight_skills = 0.6
            
        weight_text = 1.0 - weight_skills
        
        final_score = (skill_overlap_score * weight_skills) + (text_sim_score * weight_text)
        return round(final_score, 3)

    def predict_trained_model(
        self,
        resume_text: str,
        job_text: str,
        resume_skills: list[str],
        job_skills: list[str],
    ) -> dict[str, Any]:
        """
        Run inference using the serialized Scikit-learn CompatibilityPipeline artifact.
        """
        try:
            from app.ml.inference import get_ml_inference_engine
            engine = get_ml_inference_engine()
            return engine.predict(
                resume_text=resume_text,
                job_text=job_text,
                resume_skills=resume_skills,
                job_skills=job_skills,
            )
        except Exception as exc:
            logger.warning("Error invoking trained ML model (%s); falling back to heuristic", exc)
            overlap = self.calculate_skill_overlap(resume_skills, job_skills)
            score = overlap.get("overlap_score", 0.0)
            return {
                "predicted_score": score,
                "match_category": "Strong Match" if score >= 0.7 else "Low Match",
                "is_match": score >= 0.7,
                "confidence": 0.85,
                "features": {"skill_overlap_ratio": score},
            }


# Global instance
_ml_service = None

def get_ml_service() -> MLService:
    global _ml_service
    if _ml_service is None:
        _ml_service = MLService()
    return _ml_service

