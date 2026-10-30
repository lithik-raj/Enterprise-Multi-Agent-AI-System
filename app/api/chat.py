"""
Chat router — POST /api/chat

Accepts a natural-language user task, creates a task in the TaskManager,
and starts background execution across the multi-agent pipeline.

Phase 15: Guardrails integration (input guard + rate limiter).
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status

from app.models.schemas import ChatRequest, ChatResponse, TaskStatusEnum
from app.services.task_manager import get_task_manager
from app.guardrails.input_guard import get_input_guard
from app.guardrails.rate_limiter import get_rate_limiter

router = APIRouter(prefix="/api", tags=["Chat"])
logger = logging.getLogger(__name__)


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a task via natural-language chat",
)
async def chat(request: ChatRequest, req: Request) -> ChatResponse:
    """
    Accept a user task. Returns a task_id immediately (202 Accepted).
    The client polls **GET /api/task/{task_id}** for real-time workflow state.

    Phase 15 guardrails:
    - Rate limiting: 20 calls/burst, 3 tokens/sec refill per IP
    - Input guard: injection detection, PII scrubbing, toxic filter
    """
    # ── Rate limiting ────────────────────────────────────────────────────────
    client_ip = req.client.host if req.client else "unknown"
    limiter = get_rate_limiter("chat")
    allowed, rate_info = limiter.check(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rate_info["message"],
            headers={"Retry-After": str(rate_info.get("retry_after_seconds", 1))},
        )

    # ── Input guardrail ──────────────────────────────────────────────────────
    from app.services.career_advisor import is_greeting_or_wish

    guard = get_input_guard()
    guard_result = guard.check(request.message)

    # Allow friendly greetings/wishes (e.g. 'hi', 'hey') to pass length guard
    if is_greeting_or_wish(request.message) and guard_result.blocked:
        other_violations = [v for v in guard_result.violations if "too short" not in v.lower()]
        if not other_violations:
            guard_result.passed = True
            guard_result.violations = []
            guard_result.sanitized_text = request.message.strip()

    if guard_result.blocked:
        logger.warning(
            "Input blocked | ip=%s violations=%s risk=%.2f",
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

    safe_message = guard_result.sanitized_text
    session_id = request.session_id or str(uuid.uuid4())
    task_id = str(uuid.uuid4())

    logger.info(
        "Chat request accepted | task_id=%s session_id=%s doc_count=%d pii_removed=%s",
        task_id,
        session_id,
        len(request.document_ids),
        guard_result.pii_removed,
    )

    manager = get_task_manager()
    manager.create_task(
        message=safe_message,
        task_id=task_id,
        session_id=session_id,
        document_ids=request.document_ids,
    )

    return ChatResponse(
        task_id=task_id,
        session_id=session_id,
        status=TaskStatusEnum.PENDING,
        message="Task accepted. The agent pipeline will process your request.",
        created_at=datetime.utcnow(),
    )
