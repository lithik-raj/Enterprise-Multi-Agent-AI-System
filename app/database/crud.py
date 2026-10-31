"""
database/crud.py

Async CRUD (Create, Read, Update, Delete) operations for all ORM models.

These functions are the ONLY way the application writes to or reads from
the database — they are the data-access layer (DAL).

Each function accepts an AsyncSession and returns ORM objects or None.
Callers are responsible for committing/rolling back via the session.
"""
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select, update, func
from sqlalchemy.orm import Session, selectinload

from app.database.models import AgentStepRecord, DocumentRecord, TaskRecord

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Task CRUD
# ═══════════════════════════════════════════════════════════════════


async def create_task(
    db: AsyncSession,
    task_id: str,
    user_message: str,
    status: str = "pending",
    plan: Optional[Dict[str, Any]] = None,
    agent_step_names: Optional[List[str]] = None,
    session_id: Optional[str] = None,
) -> TaskRecord:
    """
    Insert a new TaskRecord with optional initial AgentStepRecords.

    Args:
        db: Active async session.
        task_id: Pre-generated UUID string.
        user_message: The raw user query / prompt.
        status: Initial task status (usually "pending").
        plan: Orchestrator plan dict (stored as JSON).
        agent_step_names: Ordered list of agent names to pre-populate steps.
        session_id: Optional conversational session identifier.

    Returns:
        The newly created (and flushed) TaskRecord.
    """
    task = TaskRecord(
        task_id=task_id,
        status=status,
        user_message=user_message,
        session_id=session_id,
        created_at=datetime.utcnow(),
    )
    task.plan = plan

    if agent_step_names:
        for order, agent_name in enumerate(agent_step_names):
            step = AgentStepRecord(
                task_id=task_id,
                step_order=order,
                agent_name=agent_name,
                status="waiting",
            )
            task.agent_steps.append(step)

    db.add(task)
    await db.flush()  # Assigns DB-generated defaults; commit is caller's responsibility
    logger.debug("Created task %s in DB", task_id)
    return task


async def get_task(
    db: AsyncSession,
    task_id: str,
) -> Optional[TaskRecord]:
    """
    Fetch a single TaskRecord (with agent steps eagerly loaded).

    Returns None if not found.
    """
    stmt = (
        select(TaskRecord)
        .where(TaskRecord.task_id == task_id)
        .options(selectinload(TaskRecord.agent_steps))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_tasks(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[TaskRecord]:
    """
    Return tasks ordered by creation time (newest first).
    """
    stmt = (
        select(TaskRecord)
        .options(selectinload(TaskRecord.agent_steps))
        .order_by(TaskRecord.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def update_task_status(
    db: AsyncSession,
    task_id: str,
    status: str,
    final_answer: Optional[str] = None,
    error: Optional[str] = None,
    sources: Optional[List[str]] = None,
    evaluation: Optional[Dict[str, Any]] = None,
    completed_at: Optional[datetime] = None,
) -> bool:
    """
    Atomically update the mutable fields of a TaskRecord.

    Returns True if a row was updated, False if the task_id did not exist.
    """
    values: Dict[str, Any] = {"status": status}

    if final_answer is not None:
        values["final_answer"] = final_answer
    if error is not None:
        values["error"] = error
    if sources is not None:
        import json
        values["sources_json"] = json.dumps(sources)
    if evaluation is not None:
        import json
        values["evaluation_json"] = json.dumps(evaluation)
    if completed_at is not None:
        values["completed_at"] = completed_at

    stmt = (
        update(TaskRecord)
        .where(TaskRecord.task_id == task_id)
        .values(**values)
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount > 0


async def count_tasks_by_status(
    db: AsyncSession,
    status: str,
) -> int:
    """Return the count of tasks with the given status."""
    stmt = select(func.count()).where(TaskRecord.status == status)
    result = await db.execute(stmt)
    return result.scalar_one()


# ═══════════════════════════════════════════════════════════════════
# Agent Step CRUD
# ═══════════════════════════════════════════════════════════════════


async def update_agent_step(
    db: AsyncSession,
    task_id: str,
    agent_name: str,
    status: str,
    result_summary: Optional[str] = None,
    error: Optional[str] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
) -> bool:
    """
    Update the status + metadata of a specific agent step within a task.

    Returns True if a row was matched, False otherwise.
    """
    values: Dict[str, Any] = {"status": status}

    if result_summary is not None:
        values["result_summary"] = result_summary
    if error is not None:
        values["error"] = error
    if started_at is not None:
        values["started_at"] = started_at
    if completed_at is not None:
        values["completed_at"] = completed_at

    stmt = (
        update(AgentStepRecord)
        .where(
            AgentStepRecord.task_id == task_id,
            AgentStepRecord.agent_name == agent_name,
        )
        .values(**values)
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount > 0


# ═══════════════════════════════════════════════════════════════════
# Document CRUD
# ═══════════════════════════════════════════════════════════════════


async def create_document(
    db: AsyncSession,
    document_id: str,
    filename: str,
    file_type: str,
    size_bytes: int,
    chunk_count: int = 0,
    indexed: bool = False,
) -> DocumentRecord:
    """
    Insert a new DocumentRecord after a successful upload + RAG indexing.
    """
    doc = DocumentRecord(
        document_id=document_id,
        filename=filename,
        file_type=file_type,
        size_bytes=size_bytes,
        chunk_count=chunk_count,
        indexed=indexed,
        uploaded_at=datetime.utcnow(),
    )
    db.add(doc)
    await db.flush()
    logger.debug("Recorded document %s (%s) in DB", document_id, filename)
    return doc


async def get_document(
    db: AsyncSession,
    document_id: str,
) -> Optional[DocumentRecord]:
    """Fetch a single DocumentRecord by primary key."""
    stmt = select(DocumentRecord).where(DocumentRecord.document_id == document_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_documents(
    db: AsyncSession,
    limit: int = 100,
) -> Sequence[DocumentRecord]:
    """Return all documents ordered by upload time (newest first)."""
    stmt = (
        select(DocumentRecord)
        .order_by(DocumentRecord.uploaded_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def update_document_indexed(
    db: AsyncSession,
    document_id: str,
    chunk_count: int,
) -> bool:
    """Mark a document as successfully indexed with its final chunk count."""
    stmt = (
        update(DocumentRecord)
        .where(DocumentRecord.document_id == document_id)
        .values(indexed=True, chunk_count=chunk_count)
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount > 0


async def count_documents(db: AsyncSession) -> int:
    """Return the total number of indexed documents."""
    stmt = select(func.count()).select_from(DocumentRecord)
    result = await db.execute(stmt)
    return result.scalar_one()
