"""
app/api/ats_expansion.py

ATS Integration and Internal Mobility API Router:
- Greenhouse, Lever, and Workday candidate import and decision synchronization
- Internal employee mobility suggestions and upskilling pathways
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.internal_mobility_agent import (
    InternalEmployee,
    InternalMobilityAgent,
    InternalMobilityMatch,
)
from app.agents.job_analyzer_agent import JobAnalyzerAgent
from app.core.auth import AuthUser, UserRole
from app.database.base import get_db
from app.database.models import AuditLogRecord, JobRecord
from app.dependencies import get_current_user, require_roles
from app.services.ats_integrations import ATSConnector, ATSExportResult

router = APIRouter(prefix="/api/expansion", tags=["ATS Integrations & Internal Mobility"])


class ATSSyncRequest(BaseModel):
    provider: str = Field("greenhouse", pattern="^(greenhouse|lever|workday)$")
    job_id: str
    candidates_count: int = Field(3, ge=1, le=50)


class ATSExportDecisionRequest(BaseModel):
    provider: str = Field("greenhouse", pattern="^(greenhouse|lever|workday)$")
    candidate_ats_id: str
    decision: str = Field(..., pattern="^(approve|reject|hold)$")
    reason: str = Field(..., min_length=3)


class MobilityRequest(BaseModel):
    job_id: str
    employees: List[InternalEmployee]


@router.post("/ats/sync-candidates")
def sync_candidates_from_ats(
    req: ATSSyncRequest,
    user: AuthUser = Depends(require_roles([UserRole.ADMIN, UserRole.RECRUITER])),
    db: Session = Depends(get_db),
):
    """Import candidate applications from external ATS (Greenhouse, Lever, or Workday)."""
    connector = ATSConnector(provider=req.provider)
    imported = connector.import_candidates(job_id=req.job_id, count=req.candidates_count)

    trace_id = f"tr_{uuid.uuid4().hex[:16]}"
    audit = AuditLogRecord(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        tenant_id=user.tenant_id,
        actor=user.email,
        action=f"ats_import_{req.provider}",
        payload_json=json.dumps({"provider": req.provider, "imported_count": len(imported), "job_id": req.job_id}),
        trace_id=trace_id,
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "provider": req.provider,
        "job_id": req.job_id,
        "imported_count": len(imported),
        "candidates": [c.model_dump() for c in imported],
        "trace_id": trace_id,
    }


@router.post("/ats/export-decision", response_model=ATSExportResult)
def export_decision_to_ats(
    req: ATSExportDecisionRequest,
    user: AuthUser = Depends(require_roles([UserRole.ADMIN, UserRole.RECRUITER])),
    db: Session = Depends(get_db),
):
    """Sync human recruiter decision back to the external ATS stage."""
    connector = ATSConnector(provider=req.provider)
    result = connector.export_decision(
        candidate_ats_id=req.candidate_ats_id,
        decision=req.decision,
        reason=req.reason,
    )

    audit = AuditLogRecord(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        tenant_id=user.tenant_id,
        actor=user.email,
        action=f"ats_decision_synced_{req.provider}",
        payload_json=json.dumps(req.model_dump()),
        trace_id=f"tr_{uuid.uuid4().hex[:16]}",
    )
    db.add(audit)
    db.commit()

    return result


@router.post("/mobility/recommendations", response_model=List[InternalMobilityMatch])
def suggest_internal_mobility(
    req: MobilityRequest,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evaluate internal employees for career mobility, promotions, and upskilling pathways."""
    job_record = db.execute(
        select(JobRecord).where(JobRecord.tenant_id == user.tenant_id, JobRecord.id == req.job_id)
    ).scalar_one_or_none()
    if not job_record:
        raise HTTPException(status_code=404, detail="Job opening not found.")

    analyzer = JobAnalyzerAgent()
    job_reqs = analyzer.analyze(job_record.title, job_record.description)

    mobility_agent = InternalMobilityAgent()
    recommendations = mobility_agent.evaluate_internal_talent(req.employees, job_reqs)

    return recommendations
