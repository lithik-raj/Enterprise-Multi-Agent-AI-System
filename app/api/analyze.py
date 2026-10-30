"""
Analyze router — POST /api/analyze

Direct analysis endpoint that triggers the multi-agent pipeline explicitly.

Phase 15: Guardrails integration (stricter input guard + rate limiter).
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status

from app.models.schemas import AnalyzeRequest, AnalyzeResponse, TaskStatusEnum
from app.services.task_manager import get_task_manager
from app.guardrails.input_guard import get_input_guard
from app.guardrails.rate_limiter import get_rate_limiter

router = APIRouter(prefix="/api", tags=["Analysis"])
logger = logging.getLogger(__name__)


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger the full multi-agent analysis pipeline directly",
)
async def analyze(request: AnalyzeRequest, req: Request) -> AnalyzeResponse:
    """
    Accepts a structured analysis request and returns a task_id.
    Poll **GET /api/task/{task_id}** for results.

    Phase 15 guardrails:
    - Stricter rate limiting: 5 calls/burst, 0.5 tokens/sec (heavy pipeline)
    - Input guard: injection detection, PII scrubbing
    """
    # ── Rate limiting (stricter than /chat) ─────────────────────────────────
    client_ip = req.client.host if req.client else "unknown"
    limiter = get_rate_limiter("analyze")
    allowed, rate_info = limiter.check(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rate_info["message"],
            headers={"Retry-After": str(rate_info.get("retry_after_seconds", 1))},
        )

    # ── Input guardrail ──────────────────────────────────────────────────────
    guard = get_input_guard()
    guard_result = guard.check(request.task)
    if guard_result.blocked:
        logger.warning(
            "Analyze input blocked | ip=%s violations=%s risk=%.2f",
            client_ip, guard_result.violations, guard_result.risk_score
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Input validation failed.",
                "violations": guard_result.violations,
                "risk_score": guard_result.risk_score,
            },
        )

    safe_task = guard_result.sanitized_text
    task_id = str(uuid.uuid4())

    logger.info(
        "Analyze request | task_id=%s docs=%d agents=%s pii_removed=%s",
        task_id,
        len(request.document_ids),
        request.agents,
        guard_result.pii_removed,
    )

    manager = get_task_manager()
    manager.create_task(
        message=safe_task,
        task_id=task_id,
        document_ids=request.document_ids,
        agents=request.agents,
    )

    return AnalyzeResponse(
        task_id=task_id,
        status=TaskStatusEnum.PENDING,
        message="Analysis task accepted. The agent pipeline will process your request.",
        created_at=datetime.utcnow(),
    )
