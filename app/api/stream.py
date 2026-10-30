"""
Real-Time Server-Sent Events (SSE) Streaming Router — Phase 20.

Exposes:
  GET /api/stream/{task_id}  — Stream multi-agent execution steps, transitions,
                               human-in-the-loop approvals, and completion events.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.schemas import TaskStatusEnum
from app.services.task_manager import get_task_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Streaming"])


async def sse_event_generator(task_id: str) -> AsyncGenerator[str, None]:
    """
    Asynchronous event generator yielding SSE messages for a given task.
    Streams structured JSON payloads under `data: {payload}\\n\\n`.
    """
    manager = get_task_manager()
    task = manager.tasks.get(task_id)

    # 1. Send initial state snapshot
    if task:
        snapshot = {
            "type": "snapshot",
            "task_id": task.task_id,
            "status": task.status.value if hasattr(task.status, "value") else str(task.status),
            "steps": [
                {
                    "agent": s.agent.value if hasattr(s.agent, "value") else str(s.agent),
                    "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                    "result_summary": s.result_summary or "",
                }
                for s in (task.agent_steps or [])
            ],
            "final_answer": task.final_answer or "",
        }
        yield f"data: {json.dumps(snapshot)}\n\n"

        # If task is already done, terminate stream immediately
        if task.status in (TaskStatusEnum.COMPLETED, TaskStatusEnum.FAILED):
            terminal_event = {
                "type": "complete" if task.status == TaskStatusEnum.COMPLETED else "error",
                "task_id": task_id,
                "status": task.status.value if hasattr(task.status, "value") else str(task.status),
                "final_answer": task.final_answer or "",
            }
            yield f"data: {json.dumps(terminal_event)}\n\n"
            return

    # 2. Subscribe to real-time events
    queue = manager.subscribe(task_id)
    try:
        while True:
            try:
                # Wait up to 3 seconds for an agent event
                event_data = await asyncio.wait_for(queue.get(), timeout=3.0)
                yield f"data: {json.dumps(event_data)}\n\n"

                # Check for termination events
                event_type = event_data.get("type")
                if event_type in ("complete", "error"):
                    break

            except asyncio.TimeoutError:
                # Keep-alive heartbeat ping
                yield ": ping\n\n"

                # Check if task finished in the background
                current_task = manager.tasks.get(task_id)
                if current_task and current_task.status in (TaskStatusEnum.COMPLETED, TaskStatusEnum.FAILED):
                    break

    except asyncio.CancelledError:
        logger.info("SSE client disconnected from stream task_id=%s", task_id)
    finally:
        manager.unsubscribe(task_id, queue)


@router.get(
    "/stream/{task_id}",
    summary="Real-time Server-Sent Events (SSE) stream for agent execution",
    response_class=StreamingResponse,
)
async def stream_task_events(task_id: str) -> StreamingResponse:
    """
    Subscribes to live multi-agent execution events for the specified task ID.
    Streams events such as step transitions, agent outputs, HITL pauses, and final completion.
    """
    if not task_id or len(task_id) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task_id format.",
        )

    return StreamingResponse(
        sse_event_generator(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
