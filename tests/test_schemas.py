"""
Phase 3 — Pydantic schema validation tests.
Run with:   pytest tests/test_schemas.py -v
"""

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AgentNameEnum,
    AgentStep,
    AgentStatusEnum,
    AnalyzeRequest,
    ApprovalAction,
    ApprovalRequest,
    ChatRequest,
    EvaluationResult,
    TaskStatusEnum,
)


# ── ChatRequest ───────────────────────────────────────────────────────────────

def test_chat_request_valid():
    req = ChatRequest(message="Analyse my resume against this job description.")
    assert req.message == "Analyse my resume against this job description."
    assert req.session_id is None
    assert req.document_ids == []


def test_chat_request_strips_whitespace():
    req = ChatRequest(message="  hello  ")
    assert req.message == "hello"


def test_chat_request_rejects_blank():
    with pytest.raises(ValidationError, match="message must not be blank"):
        ChatRequest(message="   ")


def test_chat_request_rejects_empty_string():
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_request_rejects_too_long():
    with pytest.raises(ValidationError):
        ChatRequest(message="x" * 10_001)


def test_chat_request_with_document_ids():
    req = ChatRequest(message="analyse", document_ids=["doc-1", "doc-2"])
    assert len(req.document_ids) == 2


# ── AnalyzeRequest ────────────────────────────────────────────────────────────

def test_analyze_request_valid():
    req = AnalyzeRequest(task="Compare my resume with the job description.")
    assert req.task.startswith("Compare")
    assert req.agents is None


def test_analyze_request_with_agents():
    req = AnalyzeRequest(
        task="Skill gap analysis",
        agents=[AgentNameEnum.NLP, AgentNameEnum.ML],
    )
    assert len(req.agents) == 2


def test_analyze_request_rejects_too_short():
    with pytest.raises(ValidationError):
        AnalyzeRequest(task="hi")


# ── ApprovalRequest ───────────────────────────────────────────────────────────

def test_approval_request_approve():
    req = ApprovalRequest(task_id="abc-123", action=ApprovalAction.APPROVE)
    assert req.action == "approve"


def test_approval_request_reject_with_reason():
    req = ApprovalRequest(
        task_id="abc-123",
        action=ApprovalAction.REJECT,
        reason="Wrong company.",
    )
    assert req.reason == "Wrong company."


def test_approval_request_rejects_invalid_action():
    with pytest.raises(ValidationError):
        ApprovalRequest(task_id="abc-123", action="maybe")


# ── AgentStep ─────────────────────────────────────────────────────────────────

def test_agent_step_default_status():
    step = AgentStep(agent=AgentNameEnum.ORCHESTRATOR)
    assert step.status == AgentStatusEnum.WAITING.value


def test_agent_step_invalid_agent():
    with pytest.raises(ValidationError):
        AgentStep(agent="unknown_agent")


# ── EvaluationResult ─────────────────────────────────────────────────────────

def test_evaluation_result_valid():
    ev = EvaluationResult(
        relevance=0.9,
        completeness=0.8,
        groundedness=0.7,
        task_completed=True,
        issues=[],
    )
    assert ev.relevance == 0.9


def test_evaluation_result_rejects_out_of_range():
    with pytest.raises(ValidationError):
        EvaluationResult(
            relevance=1.5,
            completeness=0.8,
            groundedness=0.7,
            task_completed=True,
        )


# ── Enum values ───────────────────────────────────────────────────────────────

def test_task_status_enum_values():
    assert TaskStatusEnum.PENDING == "pending"
    assert TaskStatusEnum.COMPLETED == "completed"


def test_agent_name_enum_values():
    assert AgentNameEnum.ORCHESTRATOR == "orchestrator"
    assert AgentNameEnum.RAG == "rag_agent"
