"""
app/services/employee_seeds.py

Canonical seed dataset containing 20 complete, realistic company employees
with full resumes, core technical competencies, and daily routine work descriptions.
Stores sample resume files in `data/employee_resumes/` for HR analysis and inspection.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
EMPLOYEE_RESUMES_DIR = WORKSPACE_ROOT / "data" / "employee_resumes"


def _generate_resume_text(
    emp_id: str,
    name: str,
    email: str,
    phone: str,
    location: str,
    designation: str,
    department: str,
    experience_years: float,
    joining_date: str,
    skills: List[str],
    routine_work: str,
    summary: str,
) -> str:
    """Generates a complete, structured corporate resume text."""
    skills_formatted = " | ".join(skills)
    return f"""================================================================================
{name.upper()}
Employee ID: {emp_id} | Official Email: {email} | Contact: {phone}
Location: {location} | Department: {department}
Current Designation: {designation} | Joining Date: {joining_date}
Industry Experience: {experience_years} Years
================================================================================

1. EXECUTIVE SUMMARY
--------------------------------------------------------------------------------
{summary}

2. DAILY ROUTINE WORK & CORE RESPONSIBILITIES
--------------------------------------------------------------------------------
{routine_work}

3. TECHNICAL SKILLS & COMPETENCIES
--------------------------------------------------------------------------------
Core Competencies: {skills_formatted}
Engineering Standards: Agile/Scrum, Git Workflows, Peer Code Reviews, CI/CD Integration
Compliance & Governance: SOC2, ISO 27001, DPDP/GDPR Data Privacy Guidelines

4. PROFESSIONAL EXPERIENCE & KEY ACHIEVEMENTS
--------------------------------------------------------------------------------
Role: {designation} — TalentGraph Enterprise Platform (2022 - Present)
- Manages high-impact deliverables across the {department} division.
- Collaborates cross-functionally with Product, AI Systems, and HR leadership.
- Drives continuous optimization of internal workflows and latency benchmarks.
- Mentors junior associates and contributes to weekly architectural reviews.

Previous Role: Associate Systems Specialist — Tech Innovations Global (Prior)
- Engineered scalable microservices and robust database integration layers.
- Authored comprehensive test suites and automated deployment manifests.
- Decreased system error rates by 35% through proactive telemetry and monitoring.

5. EDUCATION & CERTIFICATIONS
--------------------------------------------------------------------------------
- Bachelor of Technology (B.Tech) in Computer Science & Engineering
- Professional Cloud & AI Certified Practitioner
- Enterprise Security & Data Ethics Certification

================================================================================
Generated via TalentGraph Enterprise Employee Record Vault
================================================================================
"""


# ── The 20 Complete Employee Profiles ──────────────────────────────────────────

TWENTY_EMPLOYEES: List[Dict[str, Any]] = [
    {
        "employee_id": "EMP-1001",
        "name": "Priya Natarajan",
        "email": "priya.natarajan@enterprise.ai",
        "department": "Engineering",
        "designation": "Senior AI Platform Architect",
        "joining_date": "2022-03-15",
        "skills": ["Python", "PyTorch", "LangGraph", "FastAPI", "Docker", "Kubernetes", "FAISS"],
        "experience_years": 6.5,
        "status": "ACTIVE",
        "phone": "+91 98401 23456",
        "location": "Bengaluru, India",
        "notes": "Core Architect for Multi-Agent Swarm and Vector Database infrastructure.",
        "routine_work": "Orchestrates multi-agent agentic swarms, reviews LangGraph pull requests, benchmarks vector store indexing latency, and leads core agent reliability syncs with platform engineering.",
        "summary": "Accomplished AI Platform Architect with 6.5 years designing distributed agentic workflows, FAISS semantic vector search, and production FastAPI microservices handling sub-second inference.",
    },
    {
        "employee_id": "EMP-1002",
        "name": "Vikram Malhotra",
        "email": "vikram.malhotra@enterprise.ai",
        "department": "Data & AI",
        "designation": "Lead Data Scientist",
        "joining_date": "2022-08-01",
        "skills": ["Python", "Scikit-Learn", "TensorFlow", "NLP", "SQL", "MLflow", "Transformers"],
        "experience_years": 5.2,
        "status": "ACTIVE",
        "phone": "+91 98402 34567",
        "location": "Hyderabad, India",
        "notes": "Supervises candidate matching algorithms and semantic embeddings.",
        "routine_work": "Trains candidate matching models, monitors data drift using MLflow, optimizes embedding generation pipelines, and validates fairness and bias-masking evaluation metrics.",
        "summary": "Lead Data Scientist with 5.2 years experience training transformer-based NLP models, evaluating resume-job alignment, and optimizing scikit-learn regression pipelines.",
    },
    {
        "employee_id": "EMP-1003",
        "name": "Ananya Sharma",
        "email": "ananya.sharma@enterprise.ai",
        "department": "DevOps & Cloud",
        "designation": "Staff Cloud Infrastructure Engineer",
        "joining_date": "2021-11-10",
        "skills": ["AWS", "Terraform", "Docker", "Kubernetes", "CI/CD", "Linux", "Prometheus"],
        "experience_years": 7.0,
        "status": "ACTIVE",
        "phone": "+91 98403 45678",
        "location": "Pune, India",
        "notes": "Manages high-availability Kubernetes clusters and multi-region failover.",
        "routine_work": "Provisions multi-region EKS clusters via Terraform, maintains zero-downtime CI/CD deployment pipelines, audits cloud security posture, and manages Prometheus alerts.",
        "summary": "DevOps and Cloud Infrastructure Specialist with 7 years mastering AWS, Terraform, Docker containerization, and zero-downtime deployments for enterprise SaaS.",
    },
    {
        "employee_id": "EMP-1004",
        "name": "Rajesh Kanna",
        "email": "rajesh.kanna@enterprise.ai",
        "department": "Product Management",
        "designation": "Principal Technical Product Manager",
        "joining_date": "2020-05-18",
        "skills": ["Agile", "Product Roadmapping", "System Architecture", "Jira", "SQL", "User Research"],
        "experience_years": 8.5,
        "status": "ACTIVE",
        "phone": "+91 98404 56789",
        "location": "Chennai, India",
        "notes": "Product owner for autonomous screening and recruiter intelligence portals.",
        "routine_work": "Defines product specifications for autonomous recruiter screening, aligns roadmap with enterprise clients, analyzes hiring velocity metrics, and runs sprint planning.",
        "summary": "Principal Technical Product Manager with 8.5 years leading AI SaaS roadmaps, feature specifications, recruiter workflow UX, and quantitative stakeholder analytics.",
    },
    {
        "employee_id": "EMP-1005",
        "name": "Meera Sundaram",
        "email": "meera.sundaram@enterprise.ai",
        "department": "Human Resources",
        "designation": "Senior HR Business Partner & Talent Lead",
        "joining_date": "2023-01-09",
        "skills": ["Talent Acquisition", "HR Strategy", "Employee Relations", "ATS", "Onboarding", "DPDP/GDPR"],
        "experience_years": 5.5,
        "status": "ACTIVE",
        "phone": "+91 98405 67890",
        "location": "Bengaluru, India",
        "notes": "Leads workforce planning, employee onboarding, and talent governance.",
        "routine_work": "Conducts talent acquisition and executive interviews, oversees staff offboarding workflows, maintains compliance audits for DPDP/GDPR, and facilitates quarterly reviews.",
        "summary": "Senior HR Business Partner specializing in strategic workforce planning, recruitment governance, DPDP/GDPR compliance, and employee lifecycle management.",
    },
    {
        "employee_id": "EMP-1006",
        "name": "Arvind Swaminathan",
        "email": "arvind.swaminathan@enterprise.ai",
        "department": "Engineering",
        "designation": "Staff Backend Engineer",
        "joining_date": "2021-04-12",
        "skills": ["Python", "Go", "PostgreSQL", "Redis", "Apache Kafka", "Distributed Systems", "FastAPI"],
        "experience_years": 7.5,
        "status": "ACTIVE",
        "phone": "+91 98406 78901",
        "location": "Bengaluru, India",
        "notes": "High-throughput messaging and distributed transaction engine lead.",
        "routine_work": "Architects high-throughput Kafka streaming pipelines, tunes SQL query execution plans, refactors core transaction services, and reviews backend resilience tests.",
        "summary": "Staff Backend Engineer with 7.5 years scaling asynchronous message brokers (Kafka/Redis), high-concurrency microservices in Python & Go, and distributed SQL transactions.",
    },
    {
        "employee_id": "EMP-1007",
        "name": "Sneha Rao",
        "email": "sneha.rao@enterprise.ai",
        "department": "Cyber Security",
        "designation": "Principal Security Architect & Compliance Lead",
        "joining_date": "2020-09-01",
        "skills": ["SOC2", "ISO 27001", "Penetration Testing", "IAM", "OWASP", "Cryptography", "Guardrails"],
        "experience_years": 9.0,
        "status": "ACTIVE",
        "phone": "+91 98407 89012",
        "location": "Hyderabad, India",
        "notes": "Enterprise security governance, tenant isolation audits, and prompt defense.",
        "routine_work": "Conducts automated vulnerability scans, audits prompt injection defenses in LangGraph workflows, manages RBAC authorization keys, and maintains SOC2 compliance logs.",
        "summary": "Security Architect with 9 years enforcing zero-trust access control, enterprise multi-tenant database isolation, prompt injection firewall defenses, and ISO 27001 audits.",
    },
    {
        "employee_id": "EMP-1008",
        "name": "Karthik Iyer",
        "email": "karthik.iyer@enterprise.ai",
        "department": "Engineering",
        "designation": "Senior Full-Stack UI/UX Engineer",
        "joining_date": "2022-10-03",
        "skills": ["React", "TypeScript", "JavaScript", "FastAPI", "TailwindCSS", "Three.js", "REST APIs"],
        "experience_years": 4.8,
        "status": "ACTIVE",
        "phone": "+91 98408 90123",
        "location": "Chennai, India",
        "notes": "Lead for modern glassmorphic dashboard UI and 3D WebGL visualizations.",
        "routine_work": "Develops responsive interactive dashboard components, optimizes 3D WebGL visualizations, builds accessible UI modals, and connects frontend clients with FastAPI endpoints.",
        "summary": "Senior Full-Stack Engineer with 4.8 years crafting state-of-the-art WebGL/Three.js interfaces, accessible React components, and responsive enterprise dashboard architectures.",
    },
    {
        "employee_id": "EMP-1009",
        "name": "Pooja Hegde",
        "email": "pooja.hegde@enterprise.ai",
        "department": "Data & AI",
        "designation": "NLP & Large Language Models Research Engineer",
        "joining_date": "2023-04-18",
        "skills": ["PyTorch", "Hugging Face", "Transformers", "BERT", "Prompt Engineering", "Evaluation Metrics"],
        "experience_years": 4.0,
        "status": "ACTIVE",
        "phone": "+91 98409 01234",
        "location": "Bengaluru, India",
        "notes": "Fine-tuning models on domain-specific resume and job requirement datasets.",
        "routine_work": "Fine-tunes specialized domain LLMs on resume-job datasets, runs ROUGE/BLEU benchmark evals, builds automated entity extraction pipelines, and reduces model hallucination.",
        "summary": "NLP Research Engineer with 4 years specializing in Transformer architectures, Hugging Face pipelines, synthetic evaluation data generation, and structured resume parsing.",
    },
    {
        "employee_id": "EMP-1010",
        "name": "Sanjay Verma",
        "email": "sanjay.verma@enterprise.ai",
        "department": "DevOps & Cloud",
        "designation": "Senior Site Reliability Engineer (SRE)",
        "joining_date": "2022-01-24",
        "skills": ["Kubernetes", "Grafana", "Datadog", "Chaos Engineering", "Python", "Shell Scripting", "Docker"],
        "experience_years": 6.0,
        "status": "ACTIVE",
        "phone": "+91 98410 12345",
        "location": "Delhi-NCR, India",
        "notes": "SLO/SLA governance, observability pipelines, and incident mitigation.",
        "routine_work": "Monitors 99.99% platform uptime SLAs, conducts weekly chaos engineering simulations, investigates incident postmortems, and manages auto-scaling policies.",
        "summary": "Site Reliability Engineer with 6 years orchestrating Kubernetes cluster telemetry, Datadog metric dashboards, automated auto-scaling rules, and incident post-mortem analysis.",
    },
    {
        "employee_id": "EMP-1011",
        "name": "Kavita Nair",
        "email": "kavita.nair@enterprise.ai",
        "department": "QA & Reliability",
        "designation": "Lead Quality Assurance & Test Automation Engineer",
        "joining_date": "2021-07-15",
        "skills": ["Pytest", "Playwright", "Selenium", "API Testing", "Load Testing", "Locust", "CI/CD"],
        "experience_years": 5.0,
        "status": "ACTIVE",
        "phone": "+91 98411 23456",
        "location": "Pune, India",
        "notes": "Maintains 500+ unit, integration, and load test suites across CI/CD.",
        "routine_work": "Authors automated end-to-end regression suites, conducts high-concurrency load testing (500 resumes/min), audits test coverage, and inspects test logs in CI pipelines.",
        "summary": "QA Automation Lead with 5 years building scalable test automation frameworks in Pytest and Playwright, verifying cross-tenant isolation, and benchmarking API load bounds.",
    },
    {
        "employee_id": "EMP-1012",
        "name": "Rohan Deshmukh",
        "email": "rohan.deshmukh@enterprise.ai",
        "department": "Product Management",
        "designation": "Senior Product Designer & UX Lead",
        "joining_date": "2022-06-20",
        "skills": ["Figma", "User Journey Mapping", "Design Systems", "Wireframing", "UX Research", "CSS"],
        "experience_years": 5.5,
        "status": "ACTIVE",
        "phone": "+91 98412 34567",
        "location": "Mumbai, India",
        "notes": "Leads human-in-the-loop design patterns and hiring decision UI workflows.",
        "routine_work": "Designs intuitive recruitment workflows in Figma, conducts usability interviews with corporate recruiters, maintains design token libraries, and reviews visual polish.",
        "summary": "Senior Product Designer with 5.5 years designing high-fidelity design systems, intuitive data-heavy dashboards, and micro-interactions for enterprise SaaS platforms.",
    },
    {
        "employee_id": "EMP-1013",
        "name": "Divya Balaji",
        "email": "divya.balaji@enterprise.ai",
        "department": "Human Resources",
        "designation": "Talent Operations & Onboarding Specialist",
        "joining_date": "2023-09-01",
        "skills": ["Onboarding", "HRIS", "Greenhouse ATS", "Candidate Engagement", "Employee Wellness"],
        "experience_years": 3.2,
        "status": "ACTIVE",
        "phone": "+91 98413 45678",
        "location": "Bengaluru, India",
        "notes": "Specializes in smooth hiring workflows and internal employee happiness.",
        "routine_work": "Facilitates new hire documentation, manages employee record verification, coordinates candidate interview loops, and analyzes employee engagement survey data.",
        "summary": "Talent Operations Specialist with 3.2 years driving streamlined employee onboarding, ATS candidate record tracking, and HRIS integration.",
    },
    {
        "employee_id": "EMP-1014",
        "name": "Amit Sengupta",
        "email": "amit.sengupta@enterprise.ai",
        "department": "Engineering",
        "designation": "Senior Distributed Database Architect",
        "joining_date": "2020-03-10",
        "skills": ["PostgreSQL", "pgvector", "MySQL", "MongoDB", "Sharding", "Database Tuning", "High Availability"],
        "experience_years": 8.0,
        "status": "ACTIVE",
        "phone": "+91 98414 56789",
        "location": "Kolkata, India",
        "notes": "Owns multi-tenant database partitions and sub-second pgvector queries.",
        "routine_work": "Optimizes multi-tenant schema partitioning, builds disaster recovery failovers, manages pgvector similarity index benchmarks, and tunes connection pooling.",
        "summary": "Database Architect with 8 years specializing in high-throughput PostgreSQL, pgvector embedding queries, automated failover clustering, and tenant data partitioning.",
    },
    {
        "employee_id": "EMP-1015",
        "name": "Deepa Sundaram",
        "email": "deepa.sundaram@enterprise.ai",
        "department": "Data & AI",
        "designation": "Computer Vision & Document OCR Specialist",
        "joining_date": "2023-02-14",
        "skills": ["OpenCV", "Tesseract OCR", "PyTorch", "Document Parsing", "CNNs", "Image Processing"],
        "experience_years": 4.5,
        "status": "ACTIVE",
        "phone": "+91 98415 67890",
        "location": "Chennai, India",
        "notes": "Builds robust resume PDF/DOCX layout parsing and optical character recognition.",
        "routine_work": "Builds resilient multi-column PDF and image resume parsing modules, improves OCR text extraction on noisy scans, and evaluates document layout analysis models.",
        "summary": "Computer Vision & OCR Engineer with 4.5 years developing resilient multi-column document parsing models, PDF layout recognition, and automated document ingestion.",
    },
    {
        "employee_id": "EMP-1016",
        "name": "Siddharth Menon",
        "email": "siddharth.menon@enterprise.ai",
        "department": "Engineering",
        "designation": "AI Systems & Edge Deployment Engineer",
        "joining_date": "2022-05-30",
        "skills": ["ONNX", "TensorRT", "C++", "Python", "Docker", "Model Optimization", "Low-Latency Serving"],
        "experience_years": 5.8,
        "status": "ACTIVE",
        "phone": "+91 98416 78901",
        "location": "Bengaluru, India",
        "notes": "Optimizes embedding model latency with ONNX runtime and GPU quantization.",
        "routine_work": "Converts deep learning models to TensorRT and ONNX runtimes, profiles inference memory overhead, tunes GPU kernel operations, and achieves sub-100ms inference latencies.",
        "summary": "AI Systems Engineer with 5.8 years specializing in TensorRT quantization, low-latency C++ model serving, ONNX runtime execution, and GPU resource optimization.",
    },
    {
        "employee_id": "EMP-1017",
        "name": "Ritu Choudhury",
        "email": "ritu.choudhury@enterprise.ai",
        "department": "Product Management",
        "designation": "Technical Writer & AI Documentation Lead",
        "joining_date": "2023-07-03",
        "skills": ["Technical Documentation", "OpenAPI / Swagger", "Developer Guides", "Markdown", "Git"],
        "experience_years": 4.2,
        "status": "ACTIVE",
        "phone": "+91 98417 89012",
        "location": "Delhi-NCR, India",
        "notes": "Authors developer API guides, recruiter manuals, and feature how-to guides.",
        "routine_work": "Maintains developer API specifications, drafts plain-English feature guides, documents enterprise compliance steps, and curates knowledge base guides.",
        "summary": "Technical Content & Documentation Lead with 4.2 years crafting clear developer documentation, OpenAPI reference docs, architecture diagrams, and user adoption guides.",
    },
    {
        "employee_id": "EMP-1018",
        "name": "Manoj Pillai",
        "email": "manoj.pillai@enterprise.ai",
        "department": "DevOps & Cloud",
        "designation": "Cloud Security & FinOps Analyst",
        "joining_date": "2021-12-01",
        "skills": ["AWS Cost Explorer", "FinOps", "Terraform", "CloudWatch", "IAM", "Security Auditing"],
        "experience_years": 6.2,
        "status": "ACTIVE",
        "phone": "+91 98418 90123",
        "location": "Kochi, India",
        "notes": "Tracks cloud expenditures, enforces tenant cost caps, and audits IAM least privilege.",
        "routine_work": "Tracks cloud infrastructure expenditures, establishes automated per-tenant budget alerts, eliminates orphaned cloud instances, and audits least-privilege IAM policies.",
        "summary": "FinOps and Cloud Governance Specialist with 6.2 years enforcing per-tenant cloud spending caps, AWS cost optimization, and IAM security audit compliance.",
    },
    {
        "employee_id": "EMP-1019",
        "name": "Neha Joshi",
        "email": "neha.joshi@enterprise.ai",
        "department": "Human Resources",
        "designation": "Learning & Development (L&D) Partner",
        "joining_date": "2022-09-12",
        "skills": ["L&D Strategy", "Upskilling Programs", "Skill Gap Analysis", "Internal Mobility", "Coaching"],
        "experience_years": 4.8,
        "status": "ON_LEAVE",
        "phone": "+91 98419 01234",
        "location": "Pune, India",
        "notes": "Orchestrates internal mobility suggestions and upskilling pathways.",
        "routine_work": "Analyzes company-wide technical competency gaps, curates personalized upskilling pathways, tracks internal mobility transitions, and organizes technical workshops.",
        "summary": "L&D Specialist with 4.8 years designing technical upskilling programs, analyzing skill gap matrices, and driving internal mobility programs for engineering teams.",
    },
    {
        "employee_id": "EMP-1020",
        "name": "Ashwin Raman",
        "email": "ashwin.raman@enterprise.ai",
        "department": "Engineering",
        "designation": "Autonomous Agent Workflow Engineer",
        "joining_date": "2023-11-01",
        "skills": ["LangGraph", "LangChain", "Python", "Vector Search", "FastAPI", "Agentic StateGraph", "Celery"],
        "experience_years": 3.5,
        "status": "ACTIVE",
        "phone": "+91 98420 12345",
        "location": "Bengaluru, India",
        "notes": "Builds resilient LangGraph human-in-the-loop interruption checkpoints.",
        "routine_work": "Develops specialized agent subgraphs, implements human-in-the-loop interruption triggers, monitors agent execution trace IDs, and debugs multi-step decision chains.",
        "summary": "Agentic AI Workflow Engineer with 3.5 years developing LangGraph state graphs, human-in-the-loop checkpoint persistence, and distributed worker queues in Celery.",
    },
]


def ensure_resumes_on_disk() -> Dict[str, str]:
    """
    Saves all 20 individual employee resumes to `data/employee_resumes/` on disk.
    Returns mapping from employee_id to the created file path string.
    """
    resumes_dir = EMPLOYEE_RESUMES_DIR
    try:
        resumes_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        resumes_dir = Path("/tmp") / "employee_resumes"
        resumes_dir.mkdir(parents=True, exist_ok=True)
    mapping: Dict[str, str] = {}

    for emp in TWENTY_EMPLOYEES:
        emp_id = emp["employee_id"]
        safe_name = emp["name"].replace(" ", "_")
        filename = f"{emp_id}_{safe_name}_Resume.txt"
        file_path = resumes_dir / filename

        resume_body = _generate_resume_text(
            emp_id=emp_id,
            name=emp["name"],
            email=emp["email"],
            phone=emp["phone"],
            location=emp["location"],
            designation=emp["designation"],
            department=emp["department"],
            experience_years=emp["experience_years"],
            joining_date=emp["joining_date"],
            skills=emp["skills"],
            routine_work=emp["routine_work"],
            summary=emp["summary"],
        )

        emp["resume_filename"] = filename
        emp["resume_text"] = resume_body

        try:
            file_path.write_text(resume_body, encoding="utf-8")
            mapping[emp_id] = str(file_path)
        except Exception as e:
            logger.warning("Could not write resume file for %s: %s", emp_id, e)

    logger.info("Saved %d employee sample resumes to %s", len(mapping), EMPLOYEE_RESUMES_DIR)
    return mapping
