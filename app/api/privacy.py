"""
app/api/privacy.py

Privacy, DPDP Act (India), and GDPR Compliance Router:
- Candidate consent capture and timestamping
- Data Subject Access Request (DSAR) export
- Right to Erasure / Delete-on-request hard deletion
- Configurable data retention policy enforcement
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.auth import AuthUser, UserRole
from app.database.base import get_db
from app.database.models import (
    AuditLogRecord,
    CandidateRecord,
    DecisionRecord,
    MatchRecord,
    TenantRecord,
)
from app.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/api/privacy", tags=["Privacy & Compliance"])


class ConsentRequest(BaseModel):
    candidate_id: str
    consent_purpose: str = Field("Resume screening and job matching evaluation", min_length=5)
    consent_given: bool = Field(True)


class ConsentResponse(BaseModel):
    consent_id: str
    candidate_id: str
    consent_given: bool
    purpose: str
    timestamp: str
    compliance_standard: str = "DPDP Act 2023 & GDPR Art. 6"


class RetentionCleanupResponse(BaseModel):
    tenant_id: str
    retention_days_applied: int
    purged_candidates_count: int
    timestamp: str


@router.post("/consent", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
def record_candidate_consent(
    req: ConsentRequest,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record verified candidate consent under DPDP Act & GDPR."""
    consent_id = f"cns_{uuid.uuid4().hex[:12]}"
    trace_id = f"tr_{uuid.uuid4().hex[:16]}"

    audit = AuditLogRecord(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        tenant_id=user.tenant_id,
        actor=user.email,
        action="privacy_consent_recorded",
        payload_json=json.dumps({
            "consent_id": consent_id,
            "candidate_id": req.candidate_id,
            "purpose": req.consent_purpose,
            "consent_given": req.consent_given,
        }),
        trace_id=trace_id,
    )
    db.add(audit)
    db.commit()

    return ConsentResponse(
        consent_id=consent_id,
        candidate_id=req.candidate_id,
        consent_given=req.consent_given,
        purpose=req.consent_purpose,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/candidates/{candidate_id}/export")
def export_candidate_data(
    candidate_id: str,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Data Subject Access Request (DSAR): Export all personal data stored for candidate."""
    cand = db.execute(
        select(CandidateRecord).where(
            CandidateRecord.tenant_id == user.tenant_id, CandidateRecord.id == candidate_id
        )
    ).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate record not found in tenant.")

    matches = db.execute(
        select(MatchRecord).where(
            MatchRecord.tenant_id == user.tenant_id, MatchRecord.candidate_id == candidate_id
        )
    ).scalars().all()

    return {
        "candidate_id": cand.id,
        "tenant_id": cand.tenant_id,
        "source_file": cand.source_file_id,
        "profile": cand.profile,
        "masked_profile": cand.masked_profile,
        "created_at": str(cand.created_at),
        "matches_count": len(matches),
        "matches": [
            {
                "match_id": m.id,
                "score": m.score,
                "subscores": m.subscores,
                "rationale": m.rationale,
                "critic_status": m.critic_status,
            }
            for m in matches
        ],
    }


@router.delete("/candidates/{candidate_id}", status_code=status.HTTP_200_OK)
def right_to_erasure_delete_candidate(
    candidate_id: str,
    user: AuthUser = Depends(require_roles([UserRole.ADMIN, UserRole.RECRUITER])),
    db: Session = Depends(get_db),
):
    """
    Right to Erasure (GDPR Art. 17 & DPDP Sec. 12):
    Permanently deletes all candidate PII, parsed profiles, and matching records.
    """
    cand = db.execute(
        select(CandidateRecord).where(
            CandidateRecord.tenant_id == user.tenant_id, CandidateRecord.id == candidate_id
        )
    ).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    trace_id = f"tr_{uuid.uuid4().hex[:16]}"

    # Delete candidate (cascades to matches and decisions)
    db.delete(cand)

    # Record anonymized audit tombstone
    audit = AuditLogRecord(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        tenant_id=user.tenant_id,
        actor=user.email,
        action="candidate_data_erased",
        payload_json=json.dumps({"candidate_id": candidate_id, "status": "erased_permanently"}),
        trace_id=trace_id,
    )
    db.add(audit)
    db.commit()

    return {
        "status": "permanently_deleted",
        "candidate_id": candidate_id,
        "compliance_act": "DPDP 2023 / GDPR Right to Erasure",
        "trace_id": trace_id,
    }


@router.post("/retention/cleanup", response_model=RetentionCleanupResponse)
def enforce_tenant_retention_policy(
    user: AuthUser = Depends(require_roles([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """Enforces tenant-configured retention policy, purging expired candidate profiles."""
    tenant = db.execute(select(TenantRecord).where(TenantRecord.id == user.tenant_id)).scalar_one_or_none()
    retention_days = 90
    if tenant and tenant.settings and "retention_days" in tenant.settings:
        retention_days = int(tenant.settings["retention_days"])

    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    old_candidates = db.execute(
        select(CandidateRecord).where(
            CandidateRecord.tenant_id == user.tenant_id,
            CandidateRecord.created_at < cutoff_date,
        )
    ).scalars().all()

    purged_count = len(old_candidates)
    for c in old_candidates:
        db.delete(c)

    audit = AuditLogRecord(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        tenant_id=user.tenant_id,
        actor=user.email,
        action="retention_policy_executed",
        payload_json=json.dumps({"purged_count": purged_count, "retention_days": retention_days}),
        trace_id=f"tr_{uuid.uuid4().hex[:16]}",
    )
    db.add(audit)
    db.commit()

    return RetentionCleanupResponse(
        tenant_id=user.tenant_id,
        retention_days_applied=retention_days,
        purged_candidates_count=purged_count,
        timestamp=datetime.utcnow().isoformat(),
    )
