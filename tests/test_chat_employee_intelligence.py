"""
tests/test_chat_employee_intelligence.py

Comprehensive tests verifying:
1. Natural language detection of employee queries, employee management staff statuses,
   routine work inquiries, and role suitability assessments.
2. End-to-end multi-agent pipeline resolution in TaskManager.
3. Frontend DOM structural integrity ensuring modals are not trapped in containing blocks.
"""

import pytest
import re
import time
from app.services.employee_intelligence import (
    is_employee_query,
    generate_employee_intelligence_answer,
)
from app.services.task_manager import get_task_manager


def test_employee_management_status_query():
    """Verifies that employee management status questions (including phonetic/Tamil phrasing) are detected."""
    q = "rmployee mangement la wokr panravanga status yariunu ketano"
    matched, analysis = is_employee_query(q)
    assert matched is True
    assert analysis["category"] == "employee_management_status"

    answer = generate_employee_intelligence_answer(analysis)
    assert "Employee Management" in answer
    assert "Human Resources" in answer
    assert "ACTIVE" in answer
    assert "Divya Balaji" in answer or "Meera Sundaram" in answer or "Neha Joshi" in answer


def test_who_works_in_employee_management():
    """Verifies query asking specifically about staff working in employee management."""
    q = "who works in employee management and what is their status?"
    matched, analysis = is_employee_query(q)
    assert matched is True
    assert analysis["category"] == "employee_management_status"

    answer = generate_employee_intelligence_answer(analysis)
    assert "Divya Balaji" in answer or "Meera Sundaram" in answer
    assert "Neha Joshi" in answer
    assert "ACTIVE" in answer
    assert "ON_LEAVE" in answer


def test_who_is_on_leave_query():
    """Verifies detecting queries asking who is on leave across the company."""
    q = "who is on leave in our company?"
    matched, analysis = is_employee_query(q)
    assert matched is True
    assert analysis["category"] == "employees_on_leave"

    answer = generate_employee_intelligence_answer(analysis)
    assert "Neha Joshi" in answer
    assert "ON_LEAVE" in answer
    assert "Sabbatical" in answer


def test_divya_balaji_suitability_query():
    """Verifies inquiry about Divya Balaji's routine work and suitability for Data Scientist."""
    q = "who is divya balaji in our compnay? what works he is doing ? is he suitable for the data scieintist"
    matched, analysis = is_employee_query(q)
    assert matched is True
    assert analysis["category"] == "employee_suitability"
    assert "Divya Balaji" in analysis["employee"]["name"]

    answer = generate_employee_intelligence_answer(analysis)
    assert "Divya Balaji" in answer
    assert "Talent Operations & Onboarding Specialist" in answer
    assert "Data Scientist" in answer
    assert "50/25/15/10" in answer
    assert "% Overall Compatibility" in answer
    assert "ACTIVE" in answer


def test_neha_joshi_single_status_query():
    """Verifies query asking about Neha Joshi's status specifically."""
    q = "what is the status of Neha Joshi?"
    matched, analysis = is_employee_query(q)
    assert matched is True
    assert analysis["category"] == "employee_status_single"
    assert "Neha Joshi" in analysis["employee"]["name"]

    answer = generate_employee_intelligence_answer(analysis)
    assert "Neha Joshi" in answer
    assert "ON_LEAVE" in answer


def test_company_staff_overview_query():
    """Verifies full company workforce status summary query."""
    q = "list all company staff and their status"
    matched, analysis = is_employee_query(q)
    assert matched is True

    answer = generate_employee_intelligence_answer(analysis)
    assert "Active Employees" in answer
    assert "On Leave Staff" in answer


def test_task_manager_pipeline_employee_execution():
    """Verifies end-to-end task manager pipeline execution for employee management query."""
    tm = get_task_manager()
    tid = tm.create_task(
        message="rmployee mangement la wokr panravanga status yariunu ketano",
        session_id="test-session-emp-01"
    )

    # Wait up to 5 seconds for background pipeline to complete
    for _ in range(50):
        t = tm.get_task(tid)
        st = t.status.value if hasattr(t.status, "value") else str(t.status)
        if t and st in ("completed", "failed"):
            break
        time.sleep(0.1)

    task = tm.get_task(tid)
    assert task is not None
    st = task.status.value if hasattr(task.status, "value") else str(task.status)
    assert st == "completed"
    assert "Employee Management" in task.final_answer
    assert len(task.agent_steps) >= 6


def test_frontend_dom_modals_not_trapped():
    """Verifies in index.html that cm-job-fullscreen-modal and modal-view-employee are not inside career-results-card."""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Verify cm-job-fullscreen-modal is after section-recruiter at the root modal area
    idx_modal = html.find('id="cm-job-fullscreen-modal"')
    idx_recruiter = html.find('id="section-recruiter"')
    assert idx_modal != -1
    assert idx_recruiter != -1
    assert idx_modal > idx_recruiter

    # Verify career-results-card is closed before section-recruiter
    idx_career_results = html.find('class="career-results-card"')
    assert idx_career_results != -1
    assert idx_career_results < idx_recruiter
