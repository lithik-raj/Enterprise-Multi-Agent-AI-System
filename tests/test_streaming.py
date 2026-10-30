"""
Phase 20 — Real-Time Server-Sent Events (SSE) Streaming Tests.

Validates:
  GET /api/stream/{task_id}  — text/event-stream media type
  Initial state snapshot     — immediate broadcast of current task state
  Completed task streaming   — sends terminal event and closes
  Input validation           — rejects invalid task_id lengths
  Live event delivery        — broadcasts multi-agent step transitions
"""

import json
from datetime import datetime
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.task_manager import get_task_manager


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_stream_rejects_invalid_task_id(client):
    """Short or empty task_id should return 400 Bad Request."""
    resp = await client.get("/api/stream/short")
    assert resp.status_code == 400
    assert "Invalid task_id format" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_stream_completed_task_snapshot(client):
    """Streaming an already completed task should return snapshot and complete event."""
    manager = get_task_manager()
    demo_id = "task-demo-portfolio-001"
    assert demo_id in manager.tasks

    async with client.stream("GET", f"/api/stream/{demo_id}") as stream:
        assert stream.status_code == 200
        assert "text/event-stream" in stream.headers.get("content-type", "")

        events = []
        async for line in stream.aiter_lines():
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                events.append(payload)
                if payload.get("type") == "complete":
                    break

        assert len(events) >= 2
        assert events[0]["type"] == "snapshot"
        assert events[0]["task_id"] == demo_id
        assert events[1]["type"] == "complete"
        assert events[1]["status"] == "completed"


@pytest.mark.asyncio
async def test_stream_live_task_execution(client):
    """Subscribing to a running task stream receives live published events."""
    import asyncio
    manager = get_task_manager()
    test_task_id = "task-live-stream-test-999"

    # Register an active task
    from app.models.schemas import TaskResult, TaskStatusEnum, AgentStep, AgentNameEnum, AgentStatusEnum
    manager.tasks[test_task_id] = TaskResult(
        task_id=test_task_id,
        status=TaskStatusEnum.RUNNING,
        user_message="Live test stream",
        agent_steps=[
            AgentStep(agent=AgentNameEnum.ORCHESTRATOR, status=AgentStatusEnum.RUNNING),
        ],
        created_at=datetime.utcnow(),
    )

    # Publish an event shortly after connection
    async def publish_delayed_events():
        await asyncio.sleep(0.05)
        manager._publish_event(test_task_id, {
            "type": "step",
            "task_id": test_task_id,
            "agent": "research_agent",
            "status": "completed",
            "result_summary": "Discovered target company profile",
        })
        await asyncio.sleep(0.05)
        manager._publish_event(test_task_id, {
            "type": "complete",
            "task_id": test_task_id,
            "status": "completed",
            "final_answer": "Assessment finished.",
        })

    publisher = asyncio.create_task(publish_delayed_events())

    # Connect to SSE stream
    async with client.stream("GET", f"/api/stream/{test_task_id}") as stream:
        assert stream.status_code == 200
        assert "text/event-stream" in stream.headers.get("content-type", "")

        received_types = []
        async for line in stream.aiter_lines():
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                received_types.append(payload.get("type"))
                if payload.get("type") == "complete":
                    break

        await publisher
        assert "snapshot" in received_types
        assert "step" in received_types
        assert "complete" in received_types
