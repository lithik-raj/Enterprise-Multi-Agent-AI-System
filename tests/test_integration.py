"""
Phase 14 — End-to-End Integration Test Suite.

Validates the full enterprise multi-agent system described in Section 10 of the Master Prompt:
- Complete 7-agent execution: Orchestrator -> Research -> NLP -> ML -> RAG -> Recommendation -> Evaluation
- Real tool calling across search, document, ML, NLP, and RAG tools
- LangGraph StateGraph compilation and execution
- Human-in-the-Loop approval gate for consequential actions
- Full FastAPI REST API integration (/api/analyze, /api/tasks/{id}, /api/approve)
"""

from __future__ import annotations

import asyncio
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.workflows.state import AgenticState
from app.workflows.agent_graph import build_integrated_agent_graph, run_integrated_pipeline, LANGGRAPH_AVAILABLE
from app.tools.search_tools import search_company, search_jobs, get_job_details, CompanySearchInput, JobSearchInput, JobDetailsInput
from app.tools.document_tools import analyze_document, DocumentAnalysisInput
from app.tools.ml_tools import calculate_similarity, run_ml_prediction, SimilarityInput, MLPredictionInput
from app.tools.analysis_tools import extract_skills, generate_report, SkillExtractionInput, ReportInput
from app.tools.rag_tools import retrieve_knowledge, KnowledgeRetrievalInput
from app.services.task_manager import get_task_manager
from app.models.schemas import ApprovalAction, TaskStatusEnum


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


# ── 1. Tools Suite Integration Tests ─────────────────────────────────────────

def test_search_tools_integration():
    """Verify search tools return validated Pydantic models for companies and jobs."""
    comp = search_company(CompanySearchInput(company_name="DeepTech Labs"))
    assert comp.name == "DeepTech Labs"
    assert "Python" in comp.key_technologies
    assert len(comp.source_url) > 0

    jobs = search_jobs(JobSearchInput(query="AI Engineer", limit=3))
    assert jobs.total_found > 0
    assert len(jobs.jobs) <= 3
    assert any("AI" in j.title for j in jobs.jobs)

    details = get_job_details(JobDetailsInput(job_id=jobs.jobs[0].job_id))
    assert details.job_id == jobs.jobs[0].job_id
    assert len(details.required_skills) > 0


def test_document_tools_integration():
    """Verify document inspection tool extracts text and detects key sections."""
    doc_out = analyze_document(DocumentAnalysisInput(document_id="Resume"))
    assert doc_out.success is True
    assert doc_out.word_count > 50
    assert "Skills" in doc_out.identified_sections or "Experience" in doc_out.identified_sections


def test_ml_tools_integration():
    """Verify ML tools compute explainable TF-IDF similarity and compatibility predictions."""
    sim = calculate_similarity(SimilarityInput(
        text1="Python Machine Learning NLP developer with FastAPI experience",
        text2="Seeking Python ML Engineer with NLP and FastAPI",
    ))
    assert 0.2 <= sim.similarity_score <= 1.0
    assert "Cosine Similarity" in sim.algorithm

    pred = run_ml_prediction(MLPredictionInput(
        resume_skills=["Python", "Machine Learning", "NLP", "SQL"],
        job_skills=["Python", "Machine Learning", "NLP", "LangGraph", "RAG", "Vector Databases"],
        resume_text="Experienced in Python, ML, and NLP models",
        job_text="Requires Python, Machine Learning, LangGraph, and RAG systems",
        weight_skills=0.6,
    ))
    assert 0.0 < pred.overall_compatibility <= 100.0
    assert any("python" in s.lower() for s in pred.matched_skills)
    assert any("langgraph" in s.lower() for s in pred.missing_skills)
    assert "Overall Match" in pred.formula_explanation


def test_analysis_tools_integration():
    """Verify skill extraction and report generation tools."""
    extracted = extract_skills(SkillExtractionInput(
        text="Candidate proficient in Python, PyTorch, Docker, and Scikit-learn."
    ))
    assert any("python" in s.lower() for s in extracted.extracted_skills)
    assert extracted.count >= 2

    report = generate_report(ReportInput(
        company_name="DeepTech Labs",
        target_role="AI/ML Engineer",
        matched_skills=["Python", "Machine Learning"],
        missing_skills=["LangGraph", "FAISS"],
        compatibility_score=85.0,
        learning_order=["LangGraph Multi-Agent Workflows", "Vector Databases with FAISS"],
        project_proposal="Enterprise Multi-Agent AI Intelligence Platform",
    ))
    assert "85.0%" in report.report_markdown
    assert "CURRENT MATCH" in report.report_markdown
    assert "RECOMMENDED LEARNING ORDER" in report.report_markdown


def test_rag_tools_integration():
    """Verify RAG knowledge retrieval tool."""
    rag_out = retrieve_knowledge(KnowledgeRetrievalInput(
        query="LangGraph StateGraph multi-agent orchestration",
        top_k=2,
    ))
    assert rag_out.total_retrieved > 0
    assert len(rag_out.chunks) > 0
    assert len(rag_out.combined_context) > 0


# ── 2. LangGraph StateGraph Compilation & Pipeline Integration ───────────────

@pytest.mark.skipif(not LANGGRAPH_AVAILABLE, reason="LangGraph not installed")
def test_langgraph_integrated_graph_compilation():
    """Verify the 7-agent StateGraph compiles cleanly with all nodes and transitions."""
    graph = build_integrated_agent_graph()
    assert graph is not None


def test_full_7_agent_pipeline_execution():
    """
    Executes the complete Section 10 multi-agent workflow:
    Resume + Job Description + Learning Roadmap.
    Verifies all 7 agents run and enrich the state.
    """
    task = (
        "Analyze whether I match this AI/ML Engineer role at DeepTech Labs "
        "and tell me what I should learn based on my resume."
    )
    result = run_integrated_pipeline(
        task_input=task,
        document_ids=["Resume", "AI_ML_Job", "Learning_Roadmap"],
    )

    # 1. Verify all 7 steps were recorded
    agent_names = [step.agent_name for step in result["steps"]]
    assert "OrchestratorAgent" in agent_names
    assert "ResearchAgent" in agent_names
    assert "NLPAgent" in agent_names
    assert "MLAgent" in agent_names
    assert "RAGAgent" in agent_names
    assert "RecommendationAgent" in agent_names
    assert "EvaluationAgent" in agent_names

    # 2. Verify context enrichment across agents
    ctx = result["context"]
    assert "plan" in ctx
    assert "company_research" in ctx
    assert "nlp_analysis" in ctx
    assert "ml_analysis" in ctx
    assert "rag_chunks" in ctx
    assert "recommendation" in ctx
    assert "evaluation" in ctx

    # 3. Verify final answer structure matches Section 10 requirements
    final_text = result["final_answer"]
    assert "CURRENT MATCH" in final_text
    assert "Strong:" in final_text
    assert "Needs improvement:" in final_text
    assert "RECOMMENDED LEARNING ORDER:" in final_text
    assert "RECOMMENDED PORTFOLIO PROJECT:" in final_text

    # 4. Verify evaluation score
    assert result["evaluation_score"] > 0.0
    assert "Automated Multi-Agent Evaluation" in result["evaluation_feedback"]


# ── 3. Human-in-the-Loop Integration ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_hitl_consequential_workflow_pause_and_approve(client):
    """
    Verify that an action with consequential keywords (e.g. apply/outbound dispatch)
    automatically pauses execution at the HITL gate and resumes upon operator approval.
    """
    manager = get_task_manager()
    task_id = "test-hitl-consequential-001"

    manager.create_task(
        message="Submit my application and outbound message for AI/ML Engineer at DeepTech Labs.",
        task_id=task_id,
        requires_hitl=True,
    )

    # Poll until pipeline reaches HITL gate (AWAITING status)
    paused = False
    for _ in range(30):
        await asyncio.sleep(0.1)
        task = manager.get_task(task_id)
        if task.status == TaskStatusEnum.AWAITING:
            paused = True
            break

    assert paused is True
    assert task.status == TaskStatusEnum.AWAITING

    # Check pending approvals
    pending = manager.list_pending_approvals()
    assert any(p["task_id"] == task_id for p in pending)

    # Resolve approval via API
    resp = await client.post(
        "/api/approve",
        json={"task_id": task_id, "action": "approve"},
    )
    assert resp.status_code == 200

    # Poll until task completes after approval
    completed = False
    for _ in range(30):
        await asyncio.sleep(0.1)
        task = manager.get_task(task_id)
        if task.status == TaskStatusEnum.COMPLETED:
            completed = True
            break

    assert completed is True
    assert "[HITL Action Confirmed]" in task.final_answer


# ── 4. End-to-End API Integration ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_analyze_and_poll_task_completion(client):
    """
    Test direct POST /api/analyze invocation, followed by polling GET /api/tasks/{task_id}
    to observe status transition from PENDING -> RUNNING -> COMPLETED.
    """
    analyze_resp = await client.post(
        "/api/analyze",
        json={
            "task": "Analyze my skill match for AI/ML Engineer against DeepTech Labs requirements.",
            "document_ids": ["Resume", "AI_ML_Job"],
        },
    )
    assert analyze_resp.status_code == 202
    task_id = analyze_resp.json()["task_id"]
    assert len(task_id) > 0

    # Poll until completed (up to 10 seconds)
    completed = False
    for _ in range(40):
        await asyncio.sleep(0.25)
        task_resp = await client.get(f"/api/task/{task_id}")
        if task_resp.status_code == 200:
            data = task_resp.json()
            if data["status"] == "completed":
                completed = True
                assert len(data["agent_steps"]) >= 7
                assert data["evaluation"] is not None
                assert data["evaluation"]["groundedness"] > 0.0
                assert "CURRENT MATCH" in data["final_answer"]
                break

    assert completed is True
