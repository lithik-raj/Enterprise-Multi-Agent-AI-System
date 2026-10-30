"""
Phase 11 — Evaluation Service tests.
Run with:   pytest tests/test_evaluation_service.py -v
"""
import json
from unittest.mock import MagicMock

from app.services.evaluation_service import EvaluationService, EvaluationResult


# ── Heuristic tests (no LLM needed) ──────────────────────────────────────────

def test_heuristic_perfect_answer():
    svc = EvaluationService(llm_service=None)
    task = "python programming language"
    # Answer contains task tokens and is long enough to score well
    answer = ("Python is a popular python programming language used widely. "
              "It supports many paradigms including object oriented and functional. ") * 3
    result = svc.evaluate(task=task, answer=answer)
    assert isinstance(result, EvaluationResult)
    assert result.relevance > 0.0
    assert result.completeness >= 0.7   # heuristic caps at 1.0 at 50 words
    assert 0.0 <= result.overall_score <= 1.0


def test_heuristic_short_answer_penalised():
    svc = EvaluationService(llm_service=None)
    result = svc.evaluate(task="Explain Docker.", answer="It runs containers.")
    assert result.completeness < 1.0
    assert any("short" in i.lower() for i in result.issues)


def test_heuristic_irrelevant_answer():
    svc = EvaluationService(llm_service=None)
    result = svc.evaluate(task="Describe machine learning.", answer="The sky is blue and cats are cute.")
    assert result.relevance < 0.3


def test_heuristic_groundedness_with_context():
    svc = EvaluationService(llm_service=None)
    context = "FastAPI is a Python web framework. It supports async endpoints."
    answer = "FastAPI supports async endpoints."
    result = svc.evaluate(task="What is FastAPI?", answer=answer, context=context)
    assert result.groundedness > 0.5


def test_heuristic_no_context_gives_neutral_groundedness():
    svc = EvaluationService(llm_service=None)
    result = svc.evaluate(task="Tell me about AI.", answer="AI is artificial intelligence.")
    assert result.groundedness == 0.5


def test_evaluation_result_overall_score():
    r = EvaluationResult(relevance=0.8, completeness=0.6, groundedness=0.7,
                         task_completed=True, issues=[])
    assert r.overall_score == round((0.8 + 0.6 + 0.7) / 3, 4)


def test_evaluation_result_to_dict():
    r = EvaluationResult(relevance=1.0, completeness=1.0, groundedness=1.0,
                         task_completed=True, issues=[])
    d = r.to_dict()
    assert d["overall_score"] == 1.0
    assert d["task_completed"] is True


# ── LLM-based evaluation tests ────────────────────────────────────────────────

def test_llm_eval_parses_json_correctly():
    mock_llm = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = json.dumps({
        "relevance": 0.9,
        "completeness": 0.8,
        "groundedness": 0.7,
        "task_completed": True,
        "issues": []
    })
    mock_llm.generate.return_value = mock_resp

    svc = EvaluationService(llm_service=mock_llm)
    result = svc.evaluate_with_llm(task="Explain LLMs.", answer="LLMs are large models.")

    assert result.relevance == 0.9
    assert result.completeness == 0.8
    assert result.groundedness == 0.7
    assert result.task_completed is True


def test_llm_eval_falls_back_on_malformed_json():
    mock_llm = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = "Great answer! No JSON here."
    mock_llm.generate.return_value = mock_resp

    svc = EvaluationService(llm_service=mock_llm)
    result = svc.evaluate_with_llm(task="Explain LLMs.", answer="LLMs are large models.")

    # Should return mid-range fallback
    assert result.relevance == 0.5
    assert result.completeness == 0.5
    assert "Could not parse" in result.issues[0]
