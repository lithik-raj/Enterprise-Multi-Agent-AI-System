"""
All Pydantic request/response schemas for the platform.

Conventions:
- Request models end with  ...Request
- Response models end with ...Response
- Internal state models are plain dataclass-style BaseModels
- All fields have descriptions (shown in /docs)
- Use Literal types for controlled enumerations
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════════════════════════════════════
# Shared enumerations
# ═══════════════════════════════════════════════════════════════════════════════

class TaskStatusEnum(str, Enum):
    PENDING   = "pending"
    PLANNING  = "planning"
    RUNNING   = "running"
    AWAITING  = "awaiting_approval"
    COMPLETED = "completed"
    FAILED    = "failed"


class AgentStatusEnum(str, Enum):
    WAITING   = "waiting"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"


class AgentNameEnum(str, Enum):
    ORCHESTRATOR     = "orchestrator"
    RESEARCH         = "research_agent"
    NLP              = "nlp_agent"
    ML               = "ml_agent"
    RAG              = "rag_agent"
    RECOMMENDATION   = "recommendation_agent"
    EVALUATION       = "evaluation_agent"


# ═══════════════════════════════════════════════════════════════════════════════
# Agent execution tracking
# ═══════════════════════════════════════════════════════════════════════════════

class AgentStep(BaseModel):
    """Represents one agent's execution state within a workflow."""

    agent: AgentNameEnum = Field(..., description="Which agent this step belongs to")
    status: AgentStatusEnum = Field(AgentStatusEnum.WAITING, description="Current status")
    started_at: datetime | None = Field(None, description="When the agent started")
    completed_at: datetime | None = Field(None, description="When the agent finished")
    result_summary: str | None = Field(None, description="One-line summary of the result")
    error: str | None = Field(None, description="Error message if status=failed")

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════════════════════════════════════
# Chat API
# ═══════════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    """User message sent to the platform."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="The user's natural-language task or question.",
    )
    session_id: str | None = Field(
        None,
        description="Optional session identifier for conversation continuity.",
    )
    document_ids: list[str] = Field(
        default_factory=list,
        description="IDs of previously uploaded documents to include in the context.",
    )

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be blank")
        return v.strip()


class ChatResponse(BaseModel):
    """Immediate acknowledgement returned when a chat task is accepted."""

    task_id: str = Field(..., description="Unique task identifier — poll GET /api/task/{task_id}")
    session_id: str = Field(..., description="Session identifier")
    status: TaskStatusEnum = Field(TaskStatusEnum.PENDING)
    message: str = Field("Task accepted. Processing has started.")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════════════════════════════════════
# Upload API
# ═══════════════════════════════════════════════════════════════════════════════

ALLOWED_EXTENSIONS = {"pdf", "txt", "docx"}
MAX_FILE_SIZE_MB = 10


class DocumentMetadata(BaseModel):
    """Metadata record for an uploaded document."""

    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="Extension: pdf | txt | docx")
    size_bytes: int = Field(..., description="File size in bytes")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    chunk_count: int = Field(0, description="Number of chunks after RAG processing")
    indexed: bool = Field(False, description="Whether the doc has been embedded and indexed")


class UploadResponse(BaseModel):
    """Returned after a successful document upload."""

    document_id: str
    filename: str
    file_type: str
    size_bytes: int
    message: str = "Document uploaded and indexed successfully into RAG vector store."
    chunk_count: Optional[int] = 0
    extracted_preview: Optional[str] = ""


# ═══════════════════════════════════════════════════════════════════════════════
# Analyze API
# ═══════════════════════════════════════════════════════════════════════════════

class AnalyzeRequest(BaseModel):
    """Direct analysis request (bypasses chat; triggers the full agent pipeline)."""

    task: str = Field(
        ...,
        min_length=5,
        max_length=5_000,
        description="Plain-language description of what to analyse.",
    )
    document_ids: list[str] = Field(
        default_factory=list,
        description="Document IDs to use as context.",
    )
    agents: list[AgentNameEnum] | None = Field(
        None,
        description="Override agent selection. If None, the orchestrator decides.",
    )

    model_config = {"use_enum_values": True}


class AnalyzeResponse(BaseModel):
    """Returned when an analysis task is accepted."""

    task_id: str
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    message: str = "Analysis task accepted."
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════════════════════════════════════
# Task status API (GET /api/task/{task_id})
# ═══════════════════════════════════════════════════════════════════════════════

class EvaluationResult(BaseModel):
    """Structured output from the Evaluation Agent."""

    relevance: float = Field(default=1.0, ge=0.0, le=1.0)
    completeness: float = Field(default=1.0, ge=0.0, le=1.0)
    groundedness: float = Field(default=1.0, ge=0.0, le=1.0)
    task_completed: bool = Field(default=True)
    issues: list[str] = Field(default_factory=list)
    score: float | None = Field(default=None)
    decision: str | None = Field(default=None)
    explanation: str | None = Field(default=None)
    rubric_breakdown: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class TaskResult(BaseModel):
    """Complete result of a finished task."""

    task_id: str
    status: TaskStatusEnum
    user_message: str
    session_id: str | None = Field(None, description="Optional conversational session identifier")
    plan: dict[str, Any] | None = Field(None, description="Orchestrator's execution plan")
    agent_steps: list[AgentStep] = Field(default_factory=list)
    final_answer: str | None = None
    evaluation: EvaluationResult | None = None
    sources: list[str] = Field(default_factory=list, description="Retrieved document chunks / URLs")
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None

    model_config = {"use_enum_values": True, "extra": "allow"}

    def __getattr__(self, name: str) -> Any:
        if name == "session_id":
            return None
        try:
            return super().__getattr__(name)
        except Exception:
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# Approval API
# ═══════════════════════════════════════════════════════════════════════════════

class ApprovalAction(str, Enum):
    APPROVE = "approve"
    REJECT  = "reject"


class ApprovalRequest(BaseModel):
    """Human decision on a pending consequential action."""

    task_id: str = Field(..., description="Task that is awaiting approval")
    action: ApprovalAction = Field(..., description="approve | reject")
    reason: str | None = Field(None, max_length=500, description="Optional reason for rejection")

    model_config = {"use_enum_values": True}


class ApprovalResponse(BaseModel):
    """Confirmation that the approval was recorded."""

    task_id: str
    action: ApprovalAction
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════════════════════════════════════
# Error response (used by global exception handler)
# ═══════════════════════════════════════════════════════════════════════════════

class ErrorResponse(BaseModel):
    """Standard error envelope returned on 4xx / 5xx responses."""

    error: str
    detail: str | None = None
    task_id: str | None = None
