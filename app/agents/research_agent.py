"""
Research Agent.

Responsibilities:
- Research companies and organizational background.
- Research job descriptions and benchmark requirements.
- Search approved external/internal knowledge repositories.
- Collect structured information with source URLs.
- Never invent external information; handle failures gracefully.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.workflows.state import AgenticState, AgentStep
from app.tools.search_tools import search_company, search_jobs, CompanySearchInput, JobSearchInput

logger = logging.getLogger(__name__)


def run_research_agent(state: AgenticState) -> Dict[str, Any]:
    """
    Research Agent Node.
    Gathers structured intelligence about the target organization and job benchmark.
    """
    task = state.get("task_input", "")
    logger.info("ResearchAgent executing for task: %s", task)

    task_lower = task.lower()
    company_name = "Target Technology Partner"
    if "nvidia" in task_lower:
        company_name = "NVIDIA"
    elif "adobe" in task_lower:
        company_name = "Adobe"
    elif "zoho" in task_lower:
        company_name = "Zoho Corporation"
    elif "flipkart" in task_lower:
        company_name = "Flipkart"
    elif "uber" in task_lower:
        company_name = "Uber"
    elif "meta" in task_lower:
        company_name = "Meta"
    elif "ibm" in task_lower:
        company_name = "IBM"
    elif "infosys" in task_lower or "inodsys" in task_lower or "infy" in task_lower:
        company_name = "Infosys"
    elif "tcs" in task_lower or "tata consultancy" in task_lower:
        company_name = "TCS"
    elif "amazon" in task_lower or "aws" in task_lower:
        company_name = "Amazon"
    elif "accenture" in task_lower:
        company_name = "Accenture"
    elif "google" in task_lower:
        company_name = "Google"
    elif "microsoft" in task_lower:
        company_name = "Microsoft"
    elif "deeptech" in task_lower:
        company_name = "DeepTech Labs"
    elif "quantum" in task_lower:
        company_name = "Quantum AI"
    elif "abc" in task_lower:
        company_name = "ABC Technologies"

    # Call search_company tool
    company_profile = search_company(CompanySearchInput(company_name=company_name))

    # Call search_jobs tool for context
    job_search = search_jobs(JobSearchInput(query="AI Engineer", limit=3))

    step = AgentStep(
        agent_name="ResearchAgent",
        action="company_and_market_research",
        result=(
            f"Collected profile for {company_profile.name} ({company_profile.industry}). "
            f"Key tech: {', '.join(company_profile.key_technologies[:4])}. Source: {company_profile.source_url}."
        ),
        status="completed",
    )

    ctx = dict(state.get("context", {}))
    ctx["company_research"] = company_profile.model_dump()
    ctx["market_jobs"] = [j.model_dump() for j in job_search.jobs]

    return {
        "steps": [step],
        "next_node": "nlp_agent",
        "context": ctx,
    }
