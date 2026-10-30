"""
app/ml/train.py

Training Pipeline for the Resume-Job Compatibility Model.
Extracts NLP/ML features (TF-IDF cosine similarity, skill overlap, Jaccard similarity),
trains regression and classification models, computes validation metrics,
and serializes model artifacts for production inference.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import KFold

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATASET_PATH = WORKSPACE_ROOT / "data" / "datasets" / "resume_job_pairs.csv"
DEFAULT_MODEL_DIR = WORKSPACE_ROOT / "models"
MODEL_FILE_PATH = DEFAULT_MODEL_DIR / "compatibility_model.joblib"
METADATA_FILE_PATH = DEFAULT_MODEL_DIR / "model_metadata.json"


@dataclass
class TrainingMetrics:
    samples_count: int
    r2_score: float
    mean_absolute_error: float
    root_mean_squared_error: float
    classification_accuracy: float
    f1_score: float
    feature_names: List[str]
    feature_importances: Dict[str, float]


class CompatibilityFeatureExtractor:
    """Transforms raw text and skill lists into normalized feature vectors."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=500,
        )
        self.is_fitted = False

    def fit(self, texts: List[str]) -> "CompatibilityFeatureExtractor":
        self.vectorizer.fit(texts)
        self.is_fitted = True
        return self

    def extract_row_features(
        self,
        resume_text: str,
        job_text: str,
        resume_skills: List[str],
        job_skills: List[str],
    ) -> np.ndarray:
        # 1. TF-IDF Cosine Similarity
        if self.is_fitted:
            tfidf_mat = self.vectorizer.transform([resume_text, job_text])
            tfidf_sim = float(cosine_similarity(tfidf_mat[0:1], tfidf_mat[1:2])[0][0])
        else:
            tfidf_sim = 0.0

        # 2. Skill Overlap & Jaccard
        r_set = {s.strip().lower() for s in resume_skills if s.strip()}
        j_set = {s.strip().lower() for s in job_skills if s.strip()}

        intersection = len(r_set.intersection(j_set))
        union = len(r_set.union(j_set)) or 1
        j_len = len(j_set) or 1

        skill_overlap_ratio = intersection / j_len
        skill_jaccard_ratio = intersection / union
        skill_count_ratio = min(len(r_set), len(j_set)) / max(len(r_set), len(j_set), 1)

        # 3. Text Length Ratio
        r_len = len(resume_text.split()) or 1
        j_len_words = len(job_text.split()) or 1
        text_len_ratio = min(r_len, j_len_words) / max(r_len, j_len_words)

        return np.array([
            tfidf_sim,
            skill_overlap_ratio,
            skill_jaccard_ratio,
            skill_count_ratio,
            text_len_ratio,
        ], dtype=np.float32)

    def transform_dataset(
        self,
        resume_texts: List[str],
        job_texts: List[str],
        resume_skills_list: List[List[str]],
        job_skills_list: List[List[str]],
    ) -> np.ndarray:
        rows = []
        for r_txt, j_txt, r_sk, j_sk in zip(resume_texts, job_texts, resume_skills_list, job_skills_list):
            rows.append(self.extract_row_features(r_txt, j_txt, r_sk, j_sk))
        return np.vstack(rows)


class CompatibilityPipeline:
    """End-to-end trained model wrapper for regression scoring and classification."""

    FEATURE_NAMES = [
        "tfidf_cosine_similarity",
        "skill_overlap_ratio",
        "skill_jaccard_similarity",
        "skill_count_balance",
        "text_length_ratio",
    ]

    def __init__(self):
        self.feature_extractor = CompatibilityFeatureExtractor()
        self.regressor = GradientBoostingRegressor(
            n_estimators=60,
            learning_rate=0.1,
            max_depth=3,
            random_state=42,
        )
        self.classifier = RandomForestClassifier(
            n_estimators=40,
            max_depth=3,
            random_state=42,
        )

    def fit(
        self,
        resume_texts: List[str],
        job_texts: List[str],
        resume_skills_list: List[List[str]],
        job_skills_list: List[List[str]],
        scores: np.ndarray,
        labels: np.ndarray,
    ) -> TrainingMetrics:
        # Fit vectorizer across all corpus texts
        corpus = resume_texts + job_texts
        self.feature_extractor.fit(corpus)

        X = self.feature_extractor.transform_dataset(
            resume_texts, job_texts, resume_skills_list, job_skills_list
        )

        self.regressor.fit(X, scores)
        self.classifier.fit(X, labels)

        # In-sample validation metrics
        pred_scores = self.regressor.predict(X)
        pred_labels = self.classifier.predict(X)

        r2 = float(r2_score(scores, pred_scores))
        mae = float(mean_absolute_error(scores, pred_scores))
        rmse = float(np.sqrt(mean_squared_error(scores, pred_scores)))
        acc = float(accuracy_score(labels, pred_labels))
        f1 = float(f1_score(labels, pred_labels, zero_division=0))

        importances = {
            name: float(imp)
            for name, imp in zip(self.FEATURE_NAMES, self.regressor.feature_importances_)
        }

        return TrainingMetrics(
            samples_count=len(scores),
            r2_score=round(r2, 4),
            mean_absolute_error=round(mae, 4),
            root_mean_squared_error=round(rmse, 4),
            classification_accuracy=round(acc, 4),
            f1_score=round(f1, 4),
            feature_names=self.FEATURE_NAMES,
            feature_importances=importances,
        )

    def predict(
        self,
        resume_text: str,
        job_text: str,
        resume_skills: List[str],
        job_skills: List[str],
    ) -> Dict[str, Any]:
        features = self.feature_extractor.extract_row_features(
            resume_text, job_text, resume_skills, job_skills
        ).reshape(1, -1)

        pred_score = float(self.regressor.predict(features)[0])
        pred_score = max(0.0, min(1.0, pred_score))

        pred_label = int(self.classifier.predict(features)[0])
        probabilities = self.classifier.predict_proba(features)[0]
        confidence = float(probabilities[pred_label])

        feature_map = {
            name: round(float(val), 4)
            for name, val in zip(self.FEATURE_NAMES, features[0])
        }

        return {
            "predicted_score": round(pred_score, 4),
            "match_category": "Strong Match" if pred_label == 1 else "Low Match",
            "is_match": bool(pred_label == 1),
            "confidence": round(confidence, 4),
            "features": feature_map,
        }


def load_dataset(csv_path: Path) -> Tuple[List[str], List[str], List[List[str]], List[List[str]], np.ndarray, np.ndarray]:
    """Load and parse the CSV training dataset."""
    resume_texts = []
    job_texts = []
    resume_skills_list = []
    job_skills_list = []
    scores = []
    labels = []

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            resume_texts.append(row["resume_text"])
            job_texts.append(row["job_text"])
            r_sk = [s.strip() for s in row["resume_skills"].split(",") if s.strip()]
            j_sk = [s.strip() for s in row["job_skills"].split(",") if s.strip()]
            resume_skills_list.append(r_sk)
            job_skills_list.append(j_sk)
            scores.append(float(row["compatibility_score"]))
            labels.append(int(row["match_label"]))

    return (
        resume_texts,
        job_texts,
        resume_skills_list,
        job_skills_list,
        np.array(scores, dtype=np.float32),
        np.array(labels, dtype=np.int32),
    )


def train_and_save_model(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    model_dir: Path = DEFAULT_MODEL_DIR,
) -> Tuple[CompatibilityPipeline, TrainingMetrics]:
    """Train the model on dataset, evaluate metrics, and persist artifacts."""
    model_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Loading training dataset from: %s", dataset_path)

    r_texts, j_texts, r_skills, j_skills, scores, labels = load_dataset(dataset_path)

    pipeline = CompatibilityPipeline()
    metrics = pipeline.fit(r_texts, j_texts, r_skills, j_skills, scores, labels)

    model_path = model_dir / "compatibility_model.joblib"
    joblib.dump(pipeline, model_path)
    logger.info("Saved trained model to: %s", model_path)

    meta_path = model_dir / "model_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(asdict(metrics), f, indent=2)
    logger.info("Saved model metadata to: %s", meta_path)

    return pipeline, metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pipeline, metrics = train_and_save_model()
    print("=" * 60)
    print("TRAINING COMPLETED SUCCESSFULLY")
    print(f"Samples: {metrics.samples_count}")
    print(f"R² Score: {metrics.r2_score}")
    print(f"MAE: {metrics.mean_absolute_error}")
    print(f"Accuracy: {metrics.classification_accuracy * 100:.1f}%")
    print(f"F1 Score: {metrics.f1_score}")
    print("Feature Importances:", metrics.feature_importances)
    print("=" * 60)
