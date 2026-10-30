"""
Task status router — GET /api/task/{task_id}, GET /api/tasks, GET /api/stats
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import TaskResult
from app.services.task_manager import get_task_manager

router = APIRouter(prefix="/api", tags=["Tasks"])
logger = logging.getLogger(__name__)


@router.get(
    "/task/{task_id}",
    response_model=TaskResult,
    summary="Poll the status and result of a task",
)
@router.get(
    "/tasks/{task_id}",
    response_model=TaskResult,
    include_in_schema=False,
)
async def get_task(task_id: str) -> TaskResult:
    """
    Return the live status of a running, awaiting-approval, or completed task.
    """
    if not task_id or len(task_id) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task_id format.",
        )

    logger.info("Task status poll | task_id=%s", task_id)
    manager = get_task_manager()
    return manager.get_task(task_id)


@router.get(
    "/tasks",
    response_model=List[TaskResult],
    summary="List recent agent task executions",
)
async def list_tasks(limit: int = 20) -> List[TaskResult]:
    """Returns a list of recent task execution records for the dashboard."""
    manager = get_task_manager()
    return manager.list_tasks(limit=limit)


@router.get(
    "/stats",
    summary="Get platform performance & task metrics",
)
async def get_stats() -> Dict[str, Any]:
    """Returns system-wide operational metrics for the enterprise dashboard."""
    manager = get_task_manager()
    return manager.get_stats()
