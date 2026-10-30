"""
Targeted tests for:
1. Unknown candidate query (e.g. 'Satya Narayanan.') rejecting false defaults (never defaulting to Sarah Lin)
2. Irrelevant HR query guardrail (blocking out-of-domain queries like weather, cake recipes, cricket)
3. Bangalore company roles detection (Flipkart, Swiggy, Razorpay, CRED, etc.)
4. Realistic varied employee work completion (68%-88%) and explicit pending task backlogs
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.services.cognitive_qa_engine import is_irrelevant_hr_query, get_cognitive_hr_engine
from app.services.employee_service import get_employee_service
from app.api.recruiter import recruiter_voice_assist, VoiceAssistRequest


@pytest.fixture
def client():
    return TestClient(app)


def test_irrelevant_hr_guardrail():
    # Irrelevant queries must be flagged
    is_irrel, msg = is_irrelevant_hr_query("what is the recipe for chocolate cake?")
    assert is_irrel is True
    assert "HR" in msg or "recruitment" in msg

    is_irrel2, msg2 = is_irrelevant_hr_query("who won the cricket match yesterday?")
    assert is_irrel2 is True

    # Relevant HR / technical queries must NOT be flagged
    is_irrel3, _ = is_irrelevant_hr_query("tell me about python and langgraph skills for the candidate")
    assert is_irrel3 is False

    is_irrel4, _ = is_irrelevant_hr_query("what is the work status of Priya Natarajan?")
    assert is_irrel4 is False


@pytest.mark.asyncio
async def test_unknown_candidate_rejection_satya_narayanan():
    """
    Ensure querying 'Satya Narayanan.' returns candidate not found,
    and NEVER defaults to Dr. Sarah Lin or Senior AI/ML Platform Engineer.
    """
    req = VoiceAssistRequest(query="Satya Narayanan.")
    res = await recruiter_voice_assist(req)

    assert "Satya Narayanan" in res.reply_text
    assert "no candidate or employee" in res.reply_text.lower()
    # Must NOT mention Dr. Sarah Lin as the candidate being evaluated
    assert "dr. sarah lin" not in res.reply_text.lower()
    assert res.candidate_name is None


@pytest.mark.asyncio
async def test_bangalore_company_role_detection():
    """
    Ensure querying a Bangalore company (e.g., Flipkart, Swiggy, Razorpay)
    returns that specific company's role and benchmark requirements.
    """
    req_flipkart = VoiceAssistRequest(query="What are the requirements for Flipkart?")
    res_flipkart = await recruiter_voice_assist(req_flipkart)
    assert "flipkart" in res_flipkart.reply_text.lower() or "recsys" in res_flipkart.reply_text.lower()

    req_swiggy = VoiceAssistRequest(query="Tell me about open roles at Swiggy in Koramangala")
    res_swiggy = await recruiter_voice_assist(req_swiggy)
    assert "swiggy" in res_swiggy.reply_text.lower() or "dispatch" in res_swiggy.reply_text.lower()


def test_employee_work_summary_varied_completion_and_pending():
    """
    Verify get_employee_work_summary returns realistic varied completion rates (65%-88%)
    and explicit pending tasks, never hardcoded 100% for everyone.
    """
    emp_svc = get_employee_service()
    res = emp_svc.list_employees(tenant_id="default", limit=5)
    employees = res.get("employees", [])
    assert len(employees) > 0

    completion_rates = []
    for emp in employees:
        summary = emp_svc.get_employee_work_summary(emp["employee_id"], tenant_id="default")
        assert summary is not None
        rate = summary["completion_rate"]
        assert 60 <= rate <= 95  # realistic varied completion
        assert len(summary["completed_tasks"]) > 0
        assert len(summary["pending_tasks"]) > 0
        completion_rates.append(rate)

    # Confirm there is variation in completion rates across employees
    assert len(set(completion_rates)) > 1


@pytest.mark.asyncio
async def test_unknown_candidate_embedded_query():
    """
    Ensure embedded queries asking about non-existent candidates
    ('is Satya Narayanan eligible for this jobrole?') accurately report not found.
    """
    req = VoiceAssistRequest(query="is Satya Narayanan eligible for this jobrole?")
    res = await recruiter_voice_assist(req)

    assert "Satya Narayanan" in res.reply_text
    assert "no candidate or employee" in res.reply_text.lower()
    assert "dr. sarah lin" not in res.reply_text.lower()


@pytest.mark.asyncio
async def test_candidate_work_completion_and_eligibility():
    """
    Ensure queries about known candidate work completion and eligibility
    return exact verdicts without defaulting to generic filler.
    """
    # 1. Eligibility test
    req_elig = VoiceAssistRequest(query="is Dr. Sarah Lin eligible for Senior AI/ML Platform Engineer?")
    res_elig = await recruiter_voice_assist(req_elig)
    assert "eligible" in res_elig.reply_text.lower()
    assert "Sarah Lin" in res_elig.reply_text

    # 2. Work completion test
    req_work = VoiceAssistRequest(query="has Dr. Sarah Lin completed the work deliverables?")
    res_work = await recruiter_voice_assist(req_work)
    assert "completed" in res_work.reply_text.lower()
    assert "Sarah Lin" in res_work.reply_text


@pytest.mark.asyncio
async def test_employee_work_completion_and_eligibility():
    """
    Ensure queries about known employees (e.g. Priya Natarajan) accurately report
    work completion percentage, pending deliverables, and transition eligibility.
    """
    # 1. Work completion test
    req_work = VoiceAssistRequest(query="has Priya Natarajan completed the assigned work?")
    res_work = await recruiter_voice_assist(req_work)
    assert "Priya" in res_work.reply_text
    assert "percent" in res_work.reply_text.lower()
    assert "pending" in res_work.reply_text.lower()

    # 2. Eligibility test
    req_elig = VoiceAssistRequest(query="is Priya Natarajan eligible for Senior AI/ML Platform Engineer?")
    res_elig = await recruiter_voice_assist(req_elig)
    assert "Priya" in res_elig.reply_text
    assert "eligible" in res_elig.reply_text.lower()


@pytest.mark.asyncio
async def test_ram_prasad_and_chatbot_dual_query():
    """
    Ensure the user query 'Ram Prasad.\"who is chatbot' accurately:
    1. Rejects 'Ram Prasad' as not existing in the company/database.
    2. Explains that there is no candidate named 'Chatbot' in the company and identifies TalentGraph.
    3. Never falsely defaults to Arjun Mehta or Dr. Sarah Lin.
    """
    req = VoiceAssistRequest(query='Ram Prasad."who is chatbot')
    res = await recruiter_voice_assist(req)

    assert "Ram Prasad" in res.reply_text
    assert "no candidate or employee" in res.reply_text.lower()
    assert "chatbot" in res.reply_text.lower()
    assert "talentgraph" in res.reply_text.lower()
    assert "arjun mehta" not in res.reply_text.lower()
    assert "sarah lin" not in res.reply_text.lower()


@pytest.mark.asyncio
async def test_standalone_chatbot_query():
    """
    Ensure 'who is chatbot' clarifies bot identity as TalentGraph copilot
    and clarifies no candidate/employee is named Chatbot.
    """
    req = VoiceAssistRequest(query="who is chatbot")
    res = await recruiter_voice_assist(req)

    assert "talentgraph" in res.reply_text.lower()
    assert "no candidate or employee named 'chatbot'" in res.reply_text.lower()


@pytest.mark.asyncio
async def test_candidate_performance_and_working_correctness():
    """
    Ensure asking whether a candidate (e.g., Arjun Mehta) is working correctly
    and if their performance is good or bad returns grounded evaluation.
    """
    req = VoiceAssistRequest(query="is Arjun Mehta working correctly and is performance good or bad?")
    res = await recruiter_voice_assist(req)

    assert "Arjun Mehta" in res.reply_text
    assert "Working Correctness" in res.reply_text or "working correctly" in res.reply_text.lower()
    assert "Performance Rating" in res.reply_text or "performance" in res.reply_text.lower()
    assert any(term in res.reply_text.lower() for term in ["good", "moderate", "acceptable"])


@pytest.mark.asyncio
async def test_employee_performance_and_working_correctness():
    """
    Ensure asking whether an employee (e.g., Priya Natarajan) is working correctly
    and whether performance is good or bad returns deliverable metrics and working status.
    """
    req = VoiceAssistRequest(query="how is Priya Natarajan performance and is she working correctly?")
    res = await recruiter_voice_assist(req)

    assert "Priya" in res.reply_text
    assert "Working Correctness" in res.reply_text or "working correctly" in res.reply_text.lower()
    assert "Performance Rating" in res.reply_text or "performance" in res.reply_text.lower()
    assert "pending" in res.reply_text.lower() or "backlog" in res.reply_text.lower()


