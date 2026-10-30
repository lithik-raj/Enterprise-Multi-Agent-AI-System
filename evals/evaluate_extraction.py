"""
evals/evaluate_extraction.py

Golden Set Evaluation Runner for Phase 1.
Evaluates Extractor Agent performance against the golden benchmark dataset.
Calculates:
  - Skill Precision, Recall, and F1-score
  - Experience Years Mean Absolute Error & Accuracy
  - Composite Extraction Accuracy (Target: >= 95%)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.extractor_agent import ExtractorAgent


def evaluate_golden_set(golden_file_path: str = "evals/golden_set/resumes.json") -> Dict[str, Any]:
    """
    Runs the Extractor Agent across all golden set resumes and evaluates accuracy.
    """
    path = Path(golden_file_path)
    if not path.exists():
        raise FileNotFoundError(f"Golden dataset not found at {golden_file_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    extractor = ExtractorAgent()
    total_samples = len(data)

    total_skill_recall = 0.0
    total_skill_precision = 0.0
    experience_matches = 0
    total_exp_error = 0.0

    results = []

    for item in data:
        raw_text = item["text"]
        ground_truth = item["ground_truth"]
        expected_skills = set(s.lower() for s in ground_truth["skills"])
        expected_years = float(ground_truth["years_of_experience"])

        profile = extractor.extract(raw_text)
        extracted_skills = set(s.lower() for s in profile.skills)
        extracted_years = profile.years_of_experience

        # Skill metrics
        intersection = expected_skills.intersection(extracted_skills)
        recall = len(intersection) / len(expected_skills) if expected_skills else 1.0
        precision = len(intersection) / len(extracted_skills) if extracted_skills else 1.0

        total_skill_recall += recall
        total_skill_precision += precision

        # Experience metrics (within 0.5 year tolerance considered accurate)
        exp_err = abs(extracted_years - expected_years)
        total_exp_error += exp_err
        if exp_err <= 0.5:
            experience_matches += 1

        results.append({
            "id": item["id"],
            "expected_skills_count": len(expected_skills),
            "extracted_skills_count": len(extracted_skills),
            "skill_recall": round(recall, 3),
            "skill_precision": round(precision, 3),
            "expected_years": expected_years,
            "extracted_years": extracted_years,
            "exp_error": round(exp_err, 2),
        })

    avg_skill_recall = total_skill_recall / total_samples
    avg_skill_precision = total_skill_precision / total_samples
    skill_f1 = (2 * avg_skill_precision * avg_skill_recall) / (avg_skill_precision + avg_skill_recall) if (avg_skill_precision + avg_skill_recall) > 0 else 0.0
    experience_accuracy = experience_matches / total_samples
    mae_experience = total_exp_error / total_samples

    # Composite extraction score (harmonic mean of skill F1 and experience accuracy)
    composite_accuracy = (2 * skill_f1 * experience_accuracy) / (skill_f1 + experience_accuracy) if (skill_f1 + experience_accuracy) > 0 else 0.0

    report = {
        "total_resumes_evaluated": total_samples,
        "average_skill_recall": round(avg_skill_recall * 100, 2),
        "average_skill_precision": round(avg_skill_precision * 100, 2),
        "skill_f1_score": round(skill_f1 * 100, 2),
        "experience_accuracy_percentage": round(experience_accuracy * 100, 2),
        "experience_mean_absolute_error_years": round(mae_experience, 2),
        "composite_extraction_accuracy": round(composite_accuracy * 100, 2),
        "target_accuracy_met": composite_accuracy >= 0.95,
        "sample_breakdown": results,
    }

    return report


if __name__ == "__main__":
    report = evaluate_golden_set()
    print("=" * 60)
    print("TALENTGRAPH EXTRACTION EVALUATION REPORT (PHASE 1)")
    print("=" * 60)
    print(f"Total Resumes Tested:        {report['total_resumes_evaluated']}")
    print(f"Skill Recall:                {report['average_skill_recall']}%")
    print(f"Skill Precision:             {report['average_skill_precision']}%")
    print(f"Skill F1-Score:              {report['skill_f1_score']}%")
    print(f"Experience Accuracy:         {report['experience_accuracy_percentage']}%")
    print(f"Experience Mean Error:       {report['experience_mean_absolute_error_years']} yrs")
    print(f"Composite Extraction Acc:    {report['composite_extraction_accuracy']}%")
    print(f"Quality Target (>= 95%):     {'PASSED' if report['target_accuracy_met'] else 'FAILED'}")
    print("=" * 60)
