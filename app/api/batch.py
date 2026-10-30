"""
Batch Multi-Candidate Resume Ranking Router — Phase 22.

Exposes REST endpoints for bulk applicant evaluation:
  POST /api/batch/rank             — Submit multiple candidates for parallel ranking
  GET  /api/batch/{batch_id}       — Retrieve leaderboard, statistics, and scores
  GET  /api/batch/{batch_id}/export— Download ranking leaderboard as CSV
  GET  /api/batch/samples          — Retrieve ready-to-test sample candidates
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field

from app.services.batch_service import (
    BatchRankingResult,
    CandidateInput,
    get_batch_service,
)
from app.rag.loader import DocumentLoader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batch", tags=["Batch Talent Intelligence"])


class BatchRankRequest(BaseModel):
    job_title: str = Field(..., min_length=2, max_length=150)
    job_description: str = Field(..., min_length=10, max_length=15000)
    required_skills: List[str] = Field(..., min_length=1)
    candidates: List[CandidateInput] = Field(..., min_length=1, max_length=100)


@router.post(
    "/rank",
    response_model=BatchRankingResult,
    summary="Rank multiple candidates against job requirements",
    status_code=status.HTTP_200_OK,
)
async def rank_candidates_batch(request: BatchRankRequest) -> BatchRankingResult:
    """
    Evaluates candidate resumes concurrently using the trained ML model,
    sorts them into a leaderboard, and computes talent distribution analytics.
    """
    service = get_batch_service()
    try:
        return service.rank_candidates(
            job_title=request.job_title,
            job_description=request.job_description,
            required_skills=request.required_skills,
            candidates=request.candidates,
        )
    except Exception as exc:
        logger.exception("Error executing batch ranking: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch ranking failed: {str(exc)}",
        )


@router.get(
    "/samples",
    summary="Get sample candidates for 1-click batch demonstration",
)
async def get_batch_samples() -> Dict[str, Any]:
    """Returns sample enterprise candidate profiles ready for instant ranking."""
    return {
        "job_title": "Senior AI/ML Platform Engineer",
        "job_description": "Seeking Senior AI Engineer with Python, PyTorch, Transformers, LangGraph, FastAPI, and Docker deployment expertise to build scalable multi-agent systems.",
        "required_skills": ["Python", "PyTorch", "Transformers", "LangGraph", "FastAPI", "Docker"],
        "candidates": [
            {
                "name": "Dr. Sarah Lin",
                "experience_years": 6.0,
                "resume_text": "Senior AI and Deep Learning Engineer with 6 years building production PyTorch pipelines, Transformers, LangGraph agents, and FastAPI microservices on Docker and Kubernetes. PhD in Computer Science.",
                "extracted_skills": ["Python", "PyTorch", "Transformers", "LangGraph", "FastAPI", "Docker", "Deep Learning"],
            },
            {
                "name": "Alex Vance",
                "experience_years": 4.5,
                "resume_text": "Machine Learning Engineer with 4.5 years experience in Scikit-learn, PyTorch, Docker, and REST APIs. Built NLP pipelines and tabular classification models deployed on AWS.",
                "extracted_skills": ["Python", "PyTorch", "Scikit-learn", "Docker", "NLP", "REST APIs"],
            },
            {
                "name": "David Miller",
                "experience_years": 3.0,
                "resume_text": "Data Analyst transitioning to ML. 3 years SQL, Python pandas, data visualization with Tableau, and basic scikit-learn models. Familiar with Git and Docker.",
                "extracted_skills": ["Python", "SQL", "Tableau", "Scikit-learn", "Git"],
            },
            {
                "name": "Elena Gomez",
                "experience_years": 4.0,
                "resume_text": "Creative Director and Senior UI/UX Graphic Designer with 4 years specializing in Figma design systems, Adobe Creative Suite, branding guidelines, and CSS motion graphics.",
                "extracted_skills": ["Figma", "UI/UX", "Graphic Design", "CSS", "Adobe Suite"],
            },
        ],
    }


@router.get(
    "/pool",
    summary="Get extended diverse candidate pool (8 realistic profiles) for HR screening",
)
async def get_extended_batch_pool() -> Dict[str, Any]:
    """Returns a rich set of 8 realistic candidate profiles across software, ML, and cloud domains."""
    service = get_batch_service()
    return service.get_extended_sample_candidates()


class BatchDecisionRequest(BaseModel):
    candidate_name: str = Field(..., min_length=2, max_length=120)
    decision: str = Field(..., description="shortlist, interview, hire, reject")
    reason: str = Field(..., min_length=3, max_length=1000, description="Mandatory HR justification")
    recruiter_name: Optional[str] = Field("HR Hiring Lead", description="Name of recruiter taking action")


@router.post(
    "/{batch_id}/decide",
    summary="Record an HR hiring decision on a ranked candidate in a batch",
)
async def record_batch_candidate_decision(
    batch_id: str,
    payload: BatchDecisionRequest,
) -> Dict[str, Any]:
    """
    Submits a Human-in-the-Loop hiring decision (Shortlist, Interview, Hire, Reject)
    with mandatory justification, updates the batch leaderboard, logs to the audit trail,
    and returns an auto-generated Communicator candidate email draft.
    """
    service = get_batch_service()
    try:
        res = service.record_candidate_decision(
            batch_id=batch_id,
            candidate_name=payload.candidate_name,
            decision=payload.decision,
            reason=payload.reason,
            recruiter_name=payload.recruiter_name or "HR Hiring Lead",
        )
        return res
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.exception("Error recording batch decision: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not record decision: {str(exc)}",
        )


@router.get(
    "/{batch_id}",
    response_model=BatchRankingResult,
    summary="Retrieve ranked candidate leaderboard by batch ID",
)
async def get_batch_ranking(batch_id: str) -> BatchRankingResult:
    """Returns the ranked leaderboard, statistical breakdown, and individual candidate scores."""
    service = get_batch_service()
    result = service.get_batch(batch_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch '{batch_id}' not found.",
        )
    return result


@router.get(
    "/{batch_id}/export",
    summary="Export candidate leaderboard as CSV",
    response_class=Response,
)
async def export_batch_csv(batch_id: str) -> Response:
    """Exports the batch ranking leaderboard as a downloadable CSV file."""
    service = get_batch_service()
    try:
        csv_data = service.export_csv(batch_id)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="leaderboard_{batch_id}.csv"',
            },
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch '{batch_id}' not found.",
        )


@router.post(
    "/{batch_id}/sync_knowledge",
    summary="Index all batch candidate resumes into the FAISS Knowledge Database",
)
async def sync_batch_resumes_to_knowledge_base(batch_id: str) -> Dict[str, Any]:
    """
    Persists all candidate resumes from the given batch into the enterprise knowledge
    base (uploads directory) and generates chunk embeddings for FAISS vector search.
    """
    service = get_batch_service()
    try:
        return service.sync_batch_to_knowledge_base(batch_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch '{batch_id}' not found.",
        )
    except Exception as exc:
        logger.exception("Error indexing resumes to knowledge base: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index resumes to knowledge base: {str(exc)}",
        )


class IngestCandidateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Candidate or employee name")
    candidate_name: Optional[str] = Field(None, description="Candidate or employee name alias")
    email: Optional[str] = Field(None, description="Candidate contact email")
    role: Optional[str] = Field("Senior AI/ML Platform Engineer", description="Target role requisition")
    resume_text: str = Field(..., min_length=15, description="Full candidate resume or technical background text")
    experience_years: Optional[float] = Field(None, ge=0.0, le=45.0, description="Years of professional experience")
    batch_id: Optional[str] = Field("batch-demo-talent-001", description="Target batch ID")
    auto_decide: Optional[bool] = Field(True, description="Whether to automatically formulate an official decision proposal")


@router.post(
    "/ingest-candidate",
    summary="Ingest new candidate resume with 1-click end-to-end HR automation",
)
async def ingest_candidate(payload: IngestCandidateRequest) -> Dict[str, Any]:
    """
    Executes complete end-to-end HR automation for a candidate or employee:
    1. Extracts skills with NLP
    2. Stores resume into Knowledge Base and FAISS vector index
    3. Matches compatibility against requisition
    4. Formulates automated hiring decision proposal
    5. Drafts personalized Communicator email
    6. Updates active batch leaderboard
    7. Records audit trail event
    8. Synthesizes executive voice briefing
    """
    service = get_batch_service()
    try:
        resolved_name = payload.name or payload.candidate_name
        return service.ingest_candidate(
            candidate_name=resolved_name,
            resume_text=payload.resume_text,
            role=payload.role,
            email=payload.email,
            experience_years=payload.experience_years,
            batch_id=payload.batch_id or "batch-demo-talent-001",
            auto_decide=payload.auto_decide if payload.auto_decide is not None else True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.exception("Error during autonomous candidate ingestion: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Candidate ingestion failed: {str(exc)}",
        )


@router.post(
    "/upload-resume",
    summary="Upload candidate resume file (PDF, DOCX, TXT) and run complete HR automation",
)
async def upload_and_ingest_resume(
    file: UploadFile = File(...),
    role: str = Form("Senior AI/ML Platform Engineer"),
    candidate_name: Optional[str] = Form(None),
    auto_decide: bool = Form(True),
    batch_id: str = Form("batch-demo-talent-001"),
) -> Dict[str, Any]:
    """
    Accepts a candidate resume document file (PDF, DOCX, TXT, MD), parses text, and
    executes full automated HR screening, knowledge base vector indexing, scoring,
    and decision proposal.
    """
    filename = file.filename or "resume.txt"
    ext = filename.split(".")[-1].lower() if "." in filename else "txt"

    if ext not in ["txt", "pdf", "docx", "md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '.{ext}'. Supported: PDF, TXT, DOCX, MD.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        loader = DocumentLoader()
        text = loader.load(tmp_path, ext)
        if not text or len(text.strip()) < 15:
            try:
                text = content.decode("utf-8", errors="replace")
            except Exception:
                text = ""

        if not text or len(text.strip()) < 15:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract readable text from document.",
            )

        # If candidate_name not passed, try to infer from filename if clean
        clean_name = candidate_name
        if not clean_name:
            stem = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")
            if "resume" not in stem.lower() and "cv" not in stem.lower() and len(stem) <= 35:
                clean_name = stem.title()

        service = get_batch_service()
        return service.ingest_candidate(
            candidate_name=clean_name,
            resume_text=text,
            role=role,
            batch_id=batch_id,
            auto_decide=auto_decide,
        )
    finally:
        import os
        try:
            os.remove(tmp_path)
        except Exception:
            pass


