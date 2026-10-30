"""
Human-in-the-Loop approval router — POST /api/approve, GET /api/approvals
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter

from app.models.schemas import (
    ApprovalAction,
    ApprovalRequest,
    ApprovalResponse,
)
from app.services.task_manager import get_task_manager

router = APIRouter(prefix="/api", tags=["Approval"])
logger = logging.getLogger(__name__)


@router.get(
    "/approvals",
    summary="List all pending human-in-the-loop approval requests",
)
async def list_pending_approvals() -> List[Dict[str, Any]]:
    """Returns all queued decisions waiting for human operator sign-off."""
    manager = get_task_manager()
    return manager.list_pending_approvals()


@router.post(
    "/approve",
    response_model=ApprovalResponse,
    summary="Approve or reject a pending consequential agent action",
)
async def approve_action(request: ApprovalRequest) -> ApprovalResponse:
    """
    Record a human decision (approve / reject) for a pending workflow action.
    Resumes or halts the paused agent pipeline.
    """
    logger.info(
        "Approval decision | task_id=%s action=%s",
        request.task_id,
        request.action,
    )

    manager = get_task_manager()
    manager.resolve_approval(
        task_id=request.task_id,
        action=request.action,
        reason=request.reason,
    )

    if request.action == ApprovalAction.APPROVE:
        message = (
            f"Action for task '{request.task_id}' has been APPROVED. "
            "The workflow will resume."
        )
    else:
        reason = f" Reason: {request.reason}" if request.reason else ""
        message = (
            f"Action for task '{request.task_id}' has been REJECTED.{reason} "
            "The workflow has been halted."
        )

    return ApprovalResponse(
        task_id=request.task_id,
        action=request.action,
        message=message,
        timestamp=datetime.utcnow(),
    )
