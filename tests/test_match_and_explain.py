"""
tests/test_match_and_explain.py

Phase 2 Test Suite: Job Analyzer, Bias Masker, Matcher Agent (50/25/15/10 weighting),
Explainer Agent (evidence citations), and Critic Agent (hallucination defense).
"""

import pytest
from app.agents.job_analyzer_agent import JobAnalyzerAgent, JobRequirements
from app.agents.bias_masker_agent import BiasMaskerAgent, MaskedCandidateProfile
from app.agents.matcher_agent import MatcherAgent, MatchResult
from app.agents.explainer_agent import ExplainerAgent, MatchExplanation, EvidenceCitation
from app.agents.critic_agent import CriticAgent, CriticReport
from app.agents.extractor_agent import ExtractedCandidateProfile, EducationEntry


@pytest.fixture
def sample_job():
    analyzer = JobAnalyzerAgent()
    jd = (
        "We are looking for a Senior AI Engineer with 5+ years of experience.\n"
        "Requirements:\n"
        "- Strong proficiency in Python, FastAPI, and LangGraph\n"
        "- Experience with PostgreSQL and Docker\n"
        "Nice to have:\n"
        "- Experience with Kubernetes and PyTorch\n"
    )
    return analyzer.analyze("Senior AI Engineer", jd)


@pytest.fixture
def sample_candidate():
    return ExtractedCandidateProfile(
        name="Jonathan Sterling",
        email="jonathan.sterling@example.com",
        phone="+1 555-019-2834",
        skills=["Python", "Fastapi", "Langgraph", "Postgresql", "Docker", "Pytorch"],
        roles=["Senior AI Engineer", "Software Engineer"],
        years_of_experience=6.0,
        education=[EducationEntry(degree="M.S. Computer Science", institution="MIT", year="2020")],
        certifications=["AWS Certified Solutions Architect"],
        summary="Jonathan has 6 years of experience building Python and FastAPI pipelines.",
    )


def test_job_analyzer_extraction(sample_job):
    """Verify Job Analyzer accurately decomposes job descriptions."""
    assert sample_job.title == "Senior AI Engineer"
    assert sample_job.seniority == "Senior"
    assert sample_job.min_years_experience == 5.0
    assert "Python" in sample_job.must_have_skills
    assert "Fastapi" in sample_job.must_have_skills or "FastAPI" in sample_job.must_have_skills
    assert sample_job.weights.must_have == 0.50
    assert sample_job.weights.experience == 0.25
    assert sample_job.weights.semantic == 0.15
    assert sample_job.weights.nice_to_have == 0.10


def test_bias_masker_purges_pii(sample_candidate):
    """Verify Bias Masker purges name, email, phone, and gendered pronouns."""
    masker = BiasMaskerAgent()
    masked = masker.mask(sample_candidate, anon_id="Candidate_001")

    assert masked.candidate_id == "Candidate_001"
    assert "Jonathan" not in masked.masked_summary
    assert "jonathan.sterling@example.com" not in str(masked.model_dump())
    assert "+1 555-019-2834" not in str(masked.model_dump())
    assert "MIT" not in str(masked.degrees)  # school name purged
    assert "M.S. Computer Science" in masked.degrees  # degree preserved


def test_matcher_scoring_and_weights(sample_candidate, sample_job):
    """Verify Matcher Agent implements 50/25/15/10 weighting and rewards qualified candidate."""
    masker = BiasMaskerAgent()
    masked = masker.mask(sample_candidate)

    matcher = MatcherAgent()
    result = matcher.match(masked, sample_job)

    assert isinstance(result, MatchResult)
    # Qualified candidate meeting all must-haves & experience should score high (>= 85)
    assert result.overall_score >= 85.0
    assert result.subscores.must_have_score == 100.0
    assert result.subscores.experience_score == 100.0
    assert len(result.missing_must_have) == 0


def test_matcher_penalizes_missing_must_haves(sample_job):
    """Verify missing must-have skills incur hard-rule penalties."""
    underqualified_candidate = ExtractedCandidateProfile(
        name="Junior Dev",
        skills=["HTML", "CSS"],
        roles=["Junior Web Developer"],
        years_of_experience=1.0,
        education=[EducationEntry(degree="B.A. Arts", institution="College", year="2024")],
        summary="Junior web developer.",
    )
    masker = BiasMaskerAgent()
    masked = masker.mask(underqualified_candidate)

    matcher = MatcherAgent()
    result = matcher.match(masked, sample_job)

    assert result.overall_score < 50.0
    assert len(result.missing_must_have) > 0
    assert result.experience_gap_years == 4.0
    assert len(result.hard_rule_violations) >= 2


def test_explainer_agent_citations(sample_candidate, sample_job):
    """Verify Explainer Agent generates plain-language rationale with direct evidence citations."""
    masker = BiasMaskerAgent()
    masked = masker.mask(sample_candidate)
    matcher = MatcherAgent()
    match_result = matcher.match(masked, sample_job)

    explainer = ExplainerAgent()
    explanation = explainer.explain(sample_candidate, sample_job, match_result)

    assert isinstance(explanation, MatchExplanation)
    assert explanation.overall_score == match_result.overall_score
    assert len(explanation.evidence_citations) >= 3
    assert len(explanation.key_strengths) >= 1
    assert "Recommend" in explanation.human_action_recommendation


def test_critic_agent_verifies_faithful_explanation(sample_candidate, sample_job):
    """Verify Critic Agent passes faithful explanations and flags hallucinations."""
    masker = BiasMaskerAgent()
    masked = masker.mask(sample_candidate)
    matcher = MatcherAgent()
    match_result = matcher.match(masked, sample_job)

    explainer = ExplainerAgent()
    explanation = explainer.explain(sample_candidate, sample_job, match_result)

    critic = CriticAgent()
    report = critic.verify(explanation, sample_candidate)

    assert isinstance(report, CriticReport)
    assert report.status == "pass"
    assert report.faithfulness_score == 1.0
    assert report.unsupported_claims_count == 0

    # Inject hallucinated citation -> Critic must flag with 'revise'
    hallucinated_explanation = explanation.model_copy(deep=True)
    hallucinated_explanation.evidence_citations.append(
        EvidenceCitation(
            criterion="Must-Have Skill: Quantum Cryptography",
            status="matched",
            evidence_quote="Resume claims expertise in Quantum Cryptography.",
            impact_on_score="+10 pts",
        )
    )

    tampered_report = critic.verify(hallucinated_explanation, sample_candidate)
    assert tampered_report.status == "revise"
    assert tampered_report.unsupported_claims_count >= 1
    assert any("Quantum Cryptography" in claim for claim in tampered_report.unsupported_claims)
