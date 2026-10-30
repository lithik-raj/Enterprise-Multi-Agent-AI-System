"""
app/api/career.py

Career Preference & Live Hiring Matching Router.
Provides endpoints for employee preferred location selection, real company intelligence,
campus visual profiles, live hiring requisitions, and multi-criteria matching.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from app.services.career_preference_service import (
    get_career_preference_service,
    CareerPreferenceRequest,
    CareerPreferenceResponse,
    LocationOption,
    CompanyVisualProfile,
    LiveJobOpening,
)
from app.services.audit_service import get_audit_service
from app.rag.loader import DocumentLoader

router = APIRouter(prefix="/api/career", tags=["Career Preference & Live Hiring Matching"])
logger = logging.getLogger(__name__)


class ApplyIntentRequest(BaseModel):
    job_id: str = Field(..., description="Job identifier")
    company_name: str = Field(..., description="Name of company")
    candidate_name: Optional[str] = Field("Candidate", description="Name of applicant")
    candidate_email: Optional[str] = Field("applicant@example.com", description="Email of applicant")
    preferred_location: Optional[str] = Field(None, description="Candidate preferred location")


class ApplyIntentResponse(BaseModel):
    status: str
    message: str
    job_id: str
    company_name: str
    next_step: str
    apply_url: str


@router.get(
    "/locations",
    response_model=List[LocationOption],
    summary="Get all supported tech hub locations and live hiring counts",
)
async def get_supported_locations() -> List[LocationOption]:
    """Returns curated technology hub locations with active requisition counts."""
    svc = get_career_preference_service()
    return svc.get_locations()


@router.get(
    "/companies",
    response_model=List[CompanyVisualProfile],
    summary="Get verified real companies actively hiring with campus visuals",
)
async def get_active_companies() -> List[CompanyVisualProfile]:
    """Returns real companies with genuine brand logos, architectural campus banners, and hiring velocity."""
    svc = get_career_preference_service()
    return svc.get_companies()


@router.get(
    "/live-jobs",
    response_model=List[LiveJobOpening],
    summary="Get live active job openings and internships",
)
async def get_live_job_openings(
    location: Optional[str] = Query(None, description="Filter by location key, e.g. 'bengaluru', 'hyderabad', 'remote'"),
    opportunity_type: Optional[str] = Query(None, description="Filter by 'job' or 'internship'"),
) -> List[LiveJobOpening]:
    """Returns verified live hiring requisitions across global technology hubs."""
    svc = get_career_preference_service()
    return svc.get_live_jobs(location_key=location, opportunity_type=opportunity_type)


@router.post(
    "/preference-match",
    response_model=CareerPreferenceResponse,
    summary="Match candidate resume and location preferences with live hiring companies",
)
async def match_career_preferences(payload: CareerPreferenceRequest) -> CareerPreferenceResponse:
    """
    Ranks live job and internship openings at real companies matching the candidate's resume
    domain and location preferences (e.g. Bengaluru, Hyderabad, Pune, Remote).
    """
    if not payload.resume_text or len(payload.resume_text.strip()) < 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume text is too brief to analyze. Please provide at least 15 characters.",
        )

    svc = get_career_preference_service()
    result = svc.match_preferences(payload)

    # Record in audit trail
    audit_svc = get_audit_service()
    audit_svc.record(
        category="AGENT",
        action="CAREER_PREFERENCE_MATCH",
        details=f"Matched resume against {result.total_live_jobs_scanned} live requisitions. Found {result.matched_jobs_count} matches for locations: {payload.preferred_locations or ['All']} (Opportunity: {payload.opportunity_type}, Domain: {result.detected_domain}).",
        severity="info",
        metadata={
            "preferred_locations": payload.preferred_locations,
            "opportunity_type": payload.opportunity_type,
            "detected_domain": result.detected_domain,
            "domain_confidence": result.domain_confidence,
            "work_mode": payload.work_mode,
            "target_role": payload.target_role,
            "matches_found": result.matched_jobs_count,
            "top_match_score": result.matches[0].composite_score if result.matches else 0,
        },
    )

    return result


@router.post(
    "/upload-preference-match",
    response_model=CareerPreferenceResponse,
    summary="Upload resume file (PDF, TXT, DOCX, MD) and match with live hiring companies at preferred locations",
)
async def upload_and_match_preferences(
    file: UploadFile = File(...),
    preferred_locations: str = Form(""),
    opportunity_type: str = Form("all"),
    work_mode: str = Form("any"),
    target_role: str = Form("ai_ml"),
    preferred_domain: str = Form("auto"),
    min_match_score: int = Form(40),
) -> CareerPreferenceResponse:
    """Accepts a candidate resume file upload, extracts text, and matches with live hiring companies at preferred locations."""
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
                detail="Could not extract readable text from the uploaded document.",
            )

        loc_list = [l.strip().lower() for l in preferred_locations.split(",") if l.strip()]
        req = CareerPreferenceRequest(
            resume_text=text,
            preferred_locations=loc_list,
            opportunity_type=opportunity_type,
            work_mode=work_mode,
            target_role=target_role,
            preferred_domain=preferred_domain,
            min_match_score=min_match_score,
        )

        svc = get_career_preference_service()
        result = svc.match_preferences(req)

        # Record in audit trail
        audit_svc = get_audit_service()
        audit_svc.record(
            category="AGENT",
            action="CAREER_PREFERENCE_FILE_MATCH",
            details=f"Uploaded '{filename}' parsed and matched against {result.total_live_jobs_scanned} live requisitions. Found {result.matched_jobs_count} matches for locations: {loc_list or ['Auto/All']} (Opportunity: {opportunity_type}, Domain: {result.detected_domain}).",
            severity="info",
            metadata={
                "filename": filename,
                "preferred_locations": loc_list,
                "opportunity_type": opportunity_type,
                "detected_domain": result.detected_domain,
                "domain_confidence": result.domain_confidence,
                "work_mode": work_mode,
                "target_role": target_role,
                "matches_found": result.matched_jobs_count,
                "top_match_score": result.matches[0].composite_score if result.matches else 0,
            },
        )

        return result
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


@router.post(
    "/apply-intent",
    response_model=ApplyIntentResponse,
    summary="Submit application intent for a live job opening",
)
async def submit_apply_intent(payload: ApplyIntentRequest) -> ApplyIntentResponse:
    """Records application intent and logs to system audit trail."""
    svc = get_career_preference_service()
    jobs = svc.get_live_jobs()
    matching_job = next((j for j in jobs if j.job_id == payload.job_id), None)
    apply_url = matching_job.apply_url if matching_job else f"https://careers.{payload.company_name.lower().replace(' ', '')}.com"

    # Record audit event
    audit_svc = get_audit_service()
    audit_svc.record(
        category="SYSTEM",
        action="JOB_APPLICATION_INTENT",
        details=f"Candidate '{payload.candidate_name}' initiated application for '{matching_job.title if matching_job else payload.job_id}' at {payload.company_name}.",
        severity="info",
        metadata={
            "job_id": payload.job_id,
            "company": payload.company_name,
            "candidate_email": payload.candidate_email,
            "preferred_location": payload.preferred_location,
        },
    )

    return ApplyIntentResponse(
        status="recorded",
        message=f"Application intent registered for {payload.company_name}. Redirecting to official career portal.",
        job_id=payload.job_id,
        company_name=payload.company_name,
        next_step="Human approval or direct portal redirection",
        apply_url=apply_url,
    )
