"""
app/api/recovery.py

Rollback & Recovery Router (Recycle Bin & 7-Day File Retention).
Provides endpoints for viewing soft-deleted candidate resumes and staff records,
performing 1-click Rollback restoration, and executing permanent deletion.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.tenant import get_tenant_header
from app.services.recovery_service import get_recovery_service
from app.services.audit_service import get_audit_service
from app.services.batch_service import get_batch_service
from app.services.employee_service import get_employee_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recovery", tags=["Rollback & Recovery"])


class SoftDeleteRequest(BaseModel):
    item_type: str = Field(..., description="candidate | employee | document")
    item_name: str = Field(..., description="Name of candidate, employee or file")
    item_id: Optional[str] = Field(None, description="Optional ID of target entity")
    data: Dict[str, Any] = Field(default_factory=dict, description="Payload snapshot")
    reason: Optional[str] = Field("HR Soft Deletion", description="Reason for deletion")
    deleted_by: Optional[str] = Field("HR Recruiter", description="Actor performing deletion")


class SoftDeleteCandidateRequest(BaseModel):
    candidate_name: str = Field(..., description="Name of candidate")
    candidate_data: Dict[str, Any] = Field(default_factory=dict, description="Candidate details")
    reason: Optional[str] = Field("Soft deleted candidate", description="Reason for deletion")
    deleted_by: Optional[str] = Field("HR Recruiter", description="Actor performing deletion")
    tenant_id: Optional[str] = Field("default", description="Tenant ID")


class ActionResponse(BaseModel):
    success: bool
    message: str
    item_id: Optional[str] = None
    item_name: Optional[str] = None
    days_remaining: Optional[float] = None


@router.get("/items", response_model=List[Dict[str, Any]])
async def list_recovery_items(tenant_id: str = Depends(get_tenant_header)):
    """Retrieve all soft-deleted files and candidates currently held in the 7-day retention vault."""
    svc = get_recovery_service()
    return svc.list_items(tenant_id=tenant_id)


@router.get("/count")
async def get_recovery_count(tenant_id: str = Depends(get_tenant_header)):
    """Return total count of items currently in the 7-day retention vault."""
    svc = get_recovery_service()
    items = svc.list_items(tenant_id=tenant_id)
    cand_count = sum(1 for i in items if i.get("item_type") == "candidate")
    emp_count = sum(1 for i in items if i.get("item_type") == "employee")
    doc_count = sum(1 for i in items if i.get("item_type") == "document")
    return {
        "count": len(items),
        "candidates": cand_count,
        "employees": emp_count,
        "documents": doc_count,
    }


@router.post("/soft-delete-candidate", response_model=ActionResponse, status_code=status.HTTP_200_OK)
async def soft_delete_candidate(
    req: SoftDeleteCandidateRequest,
    tenant_id: str = Depends(get_tenant_header),
):
    """
    Dedicated endpoint for soft-deleting candidate profiles and moving to 7-day Recovery vault.
    """
    svc = get_recovery_service()
    audit_svc = get_audit_service()
    active_tenant = req.tenant_id or tenant_id

    # Remove from active batch leaderboard
    batch_svc = get_batch_service()
    b = batch_svc.get_batch("batch-demo-talent-001")
    payload_data = dict(req.candidate_data or {})
    if b and b.leaderboard:
        cand_matches = [c for c in b.leaderboard if c.name.lower() == req.candidate_name.lower()]
        if cand_matches and not payload_data:
            cm = cand_matches[0]
            payload_data = {
                "name": cm.name,
                "predicted_score": getattr(cm, "predicted_score", 0.75),
                "matched_skills": getattr(cm, "matched_skills", []),
                "missing_skills": getattr(cm, "missing_skills", []),
                "experience_years": getattr(cm, "experience_years", 3.0),
                "match_category": getattr(cm, "match_category", "Moderate Match"),
                "status": getattr(cm, "decision", "PENDING"),
            }
        b.leaderboard = [c for c in b.leaderboard if c.name.lower() != req.candidate_name.lower()]
        b.total_candidates = len(b.leaderboard)

    item = svc.soft_delete(
        item_type="candidate",
        item_name=req.candidate_name,
        data=payload_data,
        deleted_by=req.deleted_by or "HR Recruiter",
        reason=req.reason,
        tenant_id=active_tenant,
    )

    try:
        audit_svc.log_event(
            action="SOFT_DELETE_CANDIDATE",
            actor=req.deleted_by or "HR Recruiter",
            candidate_id=req.candidate_name,
            details=f"Candidate '{req.candidate_name}' moved to 7-day Rollback & Recovery vault. Reason: {req.reason}",
            tenant_id=active_tenant,
        )
    except Exception as e:
        logger.debug("Audit log notice: %s", e)

    return ActionResponse(
        success=True,
        message=f"'{req.candidate_name}' moved to 7-Day Rollback & Recovery vault.",
        item_id=item.item_id,
        item_name=item.item_name,
        days_remaining=item.days_remaining,
    )


@router.post("/delete", response_model=ActionResponse, status_code=status.HTTP_201_CREATED)
async def soft_delete_item(
    req: SoftDeleteRequest,
    tenant_id: str = Depends(get_tenant_header),
):
    """
    Soft-delete a candidate or employee file.
    Retains the file safely for 7 days with full rollback capability.
    """
    svc = get_recovery_service()
    audit_svc = get_audit_service()

    # If it is a candidate, remove from active batch leaderboard and preserve snapshot
    payload_data = dict(req.data or {})
    if req.item_type == "candidate":
        batch_svc = get_batch_service()
        b = batch_svc.get_batch("batch-demo-talent-001")
        if b and b.leaderboard:
            cand_matches = [c for c in b.leaderboard if c.name.lower() == req.item_name.lower()]
            if cand_matches and not payload_data:
                cm = cand_matches[0]
                payload_data = {
                    "name": cm.name,
                    "predicted_score": getattr(cm, "predicted_score", 0.75),
                    "matched_skills": getattr(cm, "matched_skills", []),
                    "missing_skills": getattr(cm, "missing_skills", []),
                    "experience_years": getattr(cm, "experience_years", 3.0),
                    "match_category": getattr(cm, "match_category", "Moderate Match"),
                    "status": getattr(cm, "decision", "PENDING"),
                }
            b.leaderboard = [c for c in b.leaderboard if c.name.lower() != req.item_name.lower()]
            b.total_candidates = len(b.leaderboard)

    item = svc.soft_delete(
        item_type=req.item_type,
        item_name=req.item_name,
        data=payload_data,
        deleted_by=req.deleted_by or "HR Recruiter",
        reason=req.reason,
        tenant_id=tenant_id,
    )

    # Log to tamper-evident audit trail
    try:
        audit_svc.log_event(
            action=f"SOFT_DELETE_{req.item_type.upper()}",
            actor=req.deleted_by or "HR Recruiter",
            candidate_id=req.item_id or req.item_name,
            details=f"Item '{req.item_name}' moved to 7-day Rollback & Recovery vault. Reason: {req.reason}",
            tenant_id=tenant_id,
        )
    except Exception as e:
        logger.debug("Audit log notice: %s", e)

    return ActionResponse(
        success=True,
        message=f"'{req.item_name}' safely moved to Rollback & Recovery. Retained for 7 days before auto-purge.",
        item_id=item.item_id,
        item_name=item.item_name,
        days_remaining=item.days_remaining,
    )


@router.post("/restore/{item_id}", response_model=ActionResponse)
@router.post("/{item_id}/restore", response_model=ActionResponse)
async def restore_item(
    item_id: str,
    actor: str = "HR Recruiter",
    tenant_id: str = Depends(get_tenant_header),
):
    """
    Rollback action: Restores a soft-deleted candidate or file back to active system tables.
    """
    svc = get_recovery_service()
    audit_svc = get_audit_service()
    item = svc.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery item '{item_id}' not found or already permanently deleted.",
        )

    item_dict = svc.restore_item(item_id, actor=actor)
    if not item_dict:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to restore item.")

    # If it was a candidate in the active batch, ensure it's re-added to batch leaderboard
    if item.item_type == "candidate":
        batch_svc = get_batch_service()
        b = batch_svc.get_batch("batch-demo-talent-001")
        if b and item.original_data:
            from app.services.batch_service import RankedCandidate
            c_name = item.item_name
            existing = any(c.name == c_name for c in b.leaderboard)
            if not existing:
                cand_obj = RankedCandidate(
                    rank=len(b.leaderboard) + 1,
                    name=c_name,
                    predicted_score=item.original_data.get("predicted_score", 0.78),
                    match_category=item.original_data.get("match_category", "Moderate Match"),
                    is_match=True,
                    confidence=0.88,
                    matched_skills=item.original_data.get("matched_skills", ["Python", "FastAPI"]),
                    missing_skills=item.original_data.get("missing_skills", ["Docker"]),
                    overlap_ratio=0.75,
                    experience_years=float(item.original_data.get("experience_years", 3.0)),
                    features={},
                    decision=item.original_data.get("status") or "RESTORED",
                )
                b.leaderboard.append(cand_obj)
                b.total_candidates = len(b.leaderboard)

    # If it was an employee, re-insert or reactivate record in Employee Management directory
    elif item.item_type == "employee":
        emp_svc = get_employee_service()
        try:
            emp_svc.restore_employee(item.original_data, tenant_id=tenant_id)
        except Exception as emp_restore_err:
            logger.error("Failed to restore employee record: %s", emp_restore_err)

    # Log audit event
    try:
        audit_svc.log_event(
            action=f"RESTORE_{item.item_type.upper()}",
            actor=actor,
            candidate_id=item.item_name,
            details=f"Item '{item.item_name}' rolled back and restored from Recovery vault.",
            tenant_id=tenant_id,
        )
    except Exception as e:
        logger.debug("Audit log notice: %s", e)

    return ActionResponse(
        success=True,
        message=f"✓ Rollback complete! '{item.item_name}' has been successfully restored.",
        item_id=item_id,
        item_name=item.item_name,
    )


@router.delete("/permanent/{item_id}", response_model=ActionResponse)
@router.delete("/{item_id}/permanent", response_model=ActionResponse)
async def permanently_delete_item(
    item_id: str,
    actor: str = "HR Recruiter",
    tenant_id: str = Depends(get_tenant_header),
):
    """
    Permanent Deletion option: Hard deletes candidate or staff record permanently.
    Safely purges any disk files and audit trails per DPDP Act 2023 & GDPR compliance.
    This action cannot be undone.
    """
    svc = get_recovery_service()
    audit_svc = get_audit_service()
    item = svc.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery item '{item_id}' not found.",
        )

    name = item.item_name
    original_data = dict(item.original_data or {})
    item_type = item.item_type

    # Securely wipe any associated disk resume files for DPDP / GDPR data privacy compliance
    resume_fn = original_data.get("resume_filename")
    if resume_fn:
        import os
        from pathlib import Path
        for folder in ["data/employee_resumes", "data/resumes", "data/uploads"]:
            fpath = Path(folder) / resume_fn
            if fpath.exists():
                try:
                    os.remove(fpath)
                    logger.info("Securely wiped file %s per permanent deletion request.", fpath)
                except Exception as wipe_err:
                    logger.warning("Could not delete file %s: %s", fpath, wipe_err)

    success = svc.permanently_delete_item(item_id, actor=actor)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to permanently delete item.")

    try:
        audit_svc.log_event(
            action="PERMANENT_HARD_DELETE",
            actor=actor,
            candidate_id=name,
            details=f"Item '{name}' ({item_type}) permanently deleted, data purged and wiped from system per compliance mandate.",
            tenant_id=tenant_id,
        )
    except Exception as e:
        logger.debug("Audit log notice: %s", e)

    return ActionResponse(
        success=True,
        message=f"✓ Permanent deletion confirmed: '{name}' has been completely purged.",
        item_id=item_id,
        item_name=name,
    )
