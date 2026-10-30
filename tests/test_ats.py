"""
Test Suite for ATS Resume & Score Analyzer Service and API.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ats_service import get_ats_service

client = TestClient(app)

SAMPLE_RESUME = """
ALEXANDER V. CHEN
AI & Machine Learning Systems Engineer
chen.alexander@example.com | +1 (555) 234-5678 | San Francisco, CA
linkedin.com/in/alexander-chen-ai | github.com/alexchen-ai

PROFESSIONAL SUMMARY:
Results-driven AI & Machine Learning Systems Engineer with 3+ years experience engineering production generative AI pipelines, multi-agent frameworks, and high-performance microservices. Spearheaded deployment of LangGraph StateGraph architectures with dense vector retrieval in FAISS, reducing query latency by 42% and processing 50K+ daily candidate assessments.

TECHNICAL COMPETENCIES & SKILLS:
- Languages: Python, Java, SQL, C++, Bash
- AI & Deep Learning: Scikit-learn, PyTorch, TensorFlow, Pandas, NumPy, Hugging Face Transformers
- Agentic & NLP Frameworks: LangGraph, RAG Pipelines, FAISS (IndexFlatL2), SentenceTransformers (384-d), spaCy
- Backend & Cloud Deployment: FastAPI, Docker, PostgreSQL, REST APIs, Git, Linux, Redis

PROFESSIONAL EXPERIENCE:
AI Engineer | Synthetix AI Labs (2023 - Present)
- Architected and deployed end-to-end multi-agent career intelligence platform using LangGraph and FastAPI, serving 12,000+ active candidates.
- Integrated dense vector retrieval using FAISS IndexFlatL2 with SentenceTransformers, achieving 34% higher semantic recall over keyword search.
- Optimized Docker container runtime and batch inference pipelines, reducing server response times to sub-85ms under peak loads.
- Implemented automated evaluation guardrails scoring groundedness, relevance, and task completeness at 96% accuracy.

Machine Learning Associate | DataSphere Tech (2021 - 2023)
- Engineered Scikit-Learn TF-IDF cosine similarity algorithms for candidate role compatibility ranking across 20+ MNC benchmarks.
- Developed automated data ingestion pipelines handling 500GB+ of unstructured resume and job description documents.
- Supervised cross-functional code reviews and spearheaded unit testing suites achieving 92% test coverage.

EDUCATION:
B.Tech in Artificial Intelligence & Data Science | First Class with Distinction (CGPA: 8.9/10)
"""


def test_ats_service_direct():
    svc = get_ats_service()
    res = svc.analyze(SAMPLE_RESUME, target_role_key="ai_ml")
    assert res.overall_score >= 65
    assert res.contact_info["email"] is True
    assert res.contact_info["linkedin"] is True
    assert res.contact_info["github"] is True
    assert res.action_verb_count >= 5
    assert res.quantifiable_metrics_count >= 2
    assert len(res.category_scores) == 5
    assert len(res.strengths) >= 2


def test_ats_api_analyze_text():
    resp = client.post(
        "/api/ats/analyze",
        json={"resume_text": SAMPLE_RESUME, "target_role": "ai_ml"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_score" in data
    assert data["overall_score"] >= 65
    assert data["target_role"] == "AI / Machine Learning Engineer"
    assert len(data["category_scores"]) == 5


def test_ats_api_rejects_blank():
    resp = client.post(
        "/api/ats/analyze",
        json={"resume_text": "   ", "target_role": "ai_ml"},
    )
    assert resp.status_code == 400


def test_ats_api_upload():
    resp = client.post(
        "/api/ats/upload-analyze",
        data={"target_role": "ai_ml"},
        files={"file": ("test_resume.txt", SAMPLE_RESUME.encode("utf-8"), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_score"] >= 65
    assert data["word_count"] > 100
