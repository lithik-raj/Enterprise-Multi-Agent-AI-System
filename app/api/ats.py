"""
ATS Router — POST /api/ats/analyze

Endpoints for Applicant Tracking System (ATS) resume scoring, formatting audit,
action verb density analysis, and keyword gap breakdown.
"""

from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.services.ats_service import get_ats_service, ATSAnalysisResult
from app.rag.loader import DocumentLoader

router = APIRouter(prefix="/api/ats", tags=["ATS Resume Analyzer"])
logger = logging.getLogger(__name__)


class ATSAnalyzeRequest(BaseModel):
    resume_text: str = Field(..., description="Full raw plain-text content of the resume")
    target_role: Optional[str] = Field("ai_ml", description="Target role key: ai_ml, software_engineer, data_scientist")


@router.post(
    "/analyze",
    response_model=ATSAnalysisResult,
    summary="Compute comprehensive ATS score and actionable recommendations",
)
async def analyze_ats_text(payload: ATSAnalyzeRequest) -> ATSAnalysisResult:
    """Analyze raw resume text and return structured ATS metrics."""
    if not payload.resume_text or len(payload.resume_text.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume text is too brief to analyze. Please provide at least 15 words.",
        )

    svc = get_ats_service()
    result = svc.analyze(payload.resume_text, target_role_key=payload.target_role or "ai_ml")
    return result


@router.post(
    "/upload-analyze",
    response_model=ATSAnalysisResult,
    summary="Upload resume file (PDF, TXT, DOCX) and run ATS analysis",
)
async def upload_and_analyze_ats(
    file: UploadFile = File(...),
    target_role: str = Form("ai_ml"),
) -> ATSAnalysisResult:
    """Accepts a file upload, parses its text, and runs full ATS evaluation."""
    filename = file.filename or "resume.txt"
    ext = filename.split(".")[-1].lower() if "." in filename else "txt"

    if ext not in ["txt", "pdf", "docx", "md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{ext}'. Supported: PDF, TXT, DOCX, MD.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    # Parse text
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        loader = DocumentLoader()
        text = loader.load(tmp_path, ext)
        if not text or len(text.strip()) < 15:
            # Fallback simple text decode if loader gave empty
            try:
                text = content.decode("utf-8", errors="replace")
            except Exception:
                text = ""

        if not text or len(text.strip()) < 15:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract readable text from the uploaded document.",
            )

        svc = get_ats_service()
        result = svc.analyze(text, target_role_key=target_role or "ai_ml")
        return result
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
