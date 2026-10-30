"""
database/models.py

SQLAlchemy ORM models for persistent task, agent-step, and document storage.

Design principles:
  - TaskRecord  →  maps 1:1 to the Pydantic TaskResult schema
  - AgentStepRecord  →  maps 1:1 to the Pydantic AgentStep schema
  - DocumentRecord  →  stores metadata for uploaded/indexed documents
  - JSON columns store nested data (plan, evaluation, sources, error)
    as JSON strings for maximum SQLite compatibility
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


# ── Task record ───────────────────────────────────────────────────────────────

class TaskRecord(Base):
    """
    Persistent representation of a multi-agent pipeline task.

    Replaces the in-memory `self.tasks: Dict[str, TaskResult]` dict
    in TaskManager with a durable SQLite row.
    """

    __tablename__ = "tasks"

    # ── Primary key ──────────────────────────────────────────────────────────
    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)

    # ── Core fields ──────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="pending")
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    final_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── JSON-encoded nested data ──────────────────────────────────────────────
    plan_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sources_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluation_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    agent_steps: Mapped[List["AgentStepRecord"]] = relationship(
        "AgentStepRecord",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="AgentStepRecord.step_order",
    )

    # ── Helper accessors ──────────────────────────────────────────────────────
    @property
    def plan(self) -> Optional[Dict[str, Any]]:
        return json.loads(self.plan_json) if self.plan_json else None

    @plan.setter
    def plan(self, value: Optional[Dict[str, Any]]) -> None:
        self.plan_json = json.dumps(value) if value is not None else None

    @property
    def sources(self) -> List[str]:
        return json.loads(self.sources_json) if self.sources_json else []

    @sources.setter
    def sources(self, value: List[str]) -> None:
        self.sources_json = json.dumps(value) if value else None

    @property
    def evaluation(self) -> Optional[Dict[str, Any]]:
        return json.loads(self.evaluation_json) if self.evaluation_json else None

    @evaluation.setter
    def evaluation(self, value: Optional[Dict[str, Any]]) -> None:
        self.evaluation_json = json.dumps(value) if value is not None else None

    def __repr__(self) -> str:
        return f"<TaskRecord id={self.task_id!r} status={self.status!r}>"


# ── Agent step record ─────────────────────────────────────────────────────────

class AgentStepRecord(Base):
    """
    One agent's execution slice within a TaskRecord.

    step_order is used for ordered reconstruction of the pipeline timeline.
    """

    __tablename__ = "agent_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False, index=True
    )

    step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="waiting")
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # ── Relationship ──────────────────────────────────────────────────────────
    task: Mapped["TaskRecord"] = relationship("TaskRecord", back_populates="agent_steps")

    def __repr__(self) -> str:
        return f"<AgentStepRecord task={self.task_id!r} agent={self.agent_name!r} status={self.status!r}>"


# ── Document record ───────────────────────────────────────────────────────────

class DocumentRecord(Base):
    """
    Metadata for a user-uploaded document that has been chunked and RAG-indexed.

    Replaces the filesystem-scan approach in `list_uploaded_documents()` with
    a queryable, structured database record.
    """

    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    indexed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<DocumentRecord id={self.document_id!r} file={self.filename!r}>"


# ═══════════════════════════════════════════════════════════════════════════════
# TalentGraph Enterprise Multi-Tenant Models (Phase 0)
# ═══════════════════════════════════════════════════════════════════════════════

class TenantRecord(Base):
    """
    Tenant entity for enterprise isolation.
    Every query and resource is partitioned by tenant_id.
    """
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(64), nullable=False, default="enterprise")
    settings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationships
    users: Mapped[List["UserRecord"]] = relationship("UserRecord", back_populates="tenant", cascade="all, delete-orphan")
    jobs: Mapped[List["JobRecord"]] = relationship("JobRecord", back_populates="tenant", cascade="all, delete-orphan")
    candidates: Mapped[List["CandidateRecord"]] = relationship("CandidateRecord", back_populates="tenant", cascade="all, delete-orphan")
    runs: Mapped[List["RunRecord"]] = relationship("RunRecord", back_populates="tenant", cascade="all, delete-orphan")

    @property
    def settings(self) -> Dict[str, Any]:
        return json.loads(self.settings_json) if self.settings_json else {}

    @settings.setter
    def settings(self, val: Dict[str, Any]) -> None:
        self.settings_json = json.dumps(val) if val is not None else None

    def __repr__(self) -> str:
        return f"<TenantRecord id={self.id!r} name={self.name!r}>"


class UserRecord(Base):
    """
    User account partitioned by tenant.
    Roles: admin, recruiter, hiring_manager, auditor.
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="recruiter")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationship
    tenant: Mapped["TenantRecord"] = relationship("TenantRecord", back_populates="users")

    def __repr__(self) -> str:
        return f"<UserRecord id={self.id!r} email={self.email!r} role={self.role!r}>"


class JobRecord(Base):
    """
    Job opening created by a recruiter within a specific tenant.
    """
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationships
    tenant: Mapped["TenantRecord"] = relationship("TenantRecord", back_populates="jobs")
    runs: Mapped[List["RunRecord"]] = relationship("RunRecord", back_populates="job", cascade="all, delete-orphan")

    @property
    def requirements(self) -> Dict[str, Any]:
        return json.loads(self.requirements_json) if self.requirements_json else {}

    @requirements.setter
    def requirements(self, val: Dict[str, Any]) -> None:
        self.requirements_json = json.dumps(val) if val is not None else None

    def __repr__(self) -> str:
        return f"<JobRecord id={self.id!r} title={self.title!r} tenant={self.tenant_id!r}>"


class CandidateRecord(Base):
    """
    Candidate resume profile belonging strictly to a tenant.
    Includes raw parsed profile, bias-masked profile, and semantic embedding.
    """
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    profile_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    masked_profile_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationships
    tenant: Mapped["TenantRecord"] = relationship("TenantRecord", back_populates="candidates")
    matches: Mapped[List["MatchRecord"]] = relationship("MatchRecord", back_populates="candidate", cascade="all, delete-orphan")

    @property
    def profile(self) -> Dict[str, Any]:
        return json.loads(self.profile_json) if self.profile_json else {}

    @profile.setter
    def profile(self, val: Dict[str, Any]) -> None:
        self.profile_json = json.dumps(val) if val is not None else None

    @property
    def masked_profile(self) -> Dict[str, Any]:
        return json.loads(self.masked_profile_json) if self.masked_profile_json else {}

    @masked_profile.setter
    def masked_profile(self, val: Dict[str, Any]) -> None:
        self.masked_profile_json = json.dumps(val) if val is not None else None

    @property
    def embedding(self) -> List[float]:
        return json.loads(self.embedding_json) if self.embedding_json else []

    @embedding.setter
    def embedding(self, val: List[float]) -> None:
        self.embedding_json = json.dumps(val) if val is not None else None

    def __repr__(self) -> str:
        return f"<CandidateRecord id={self.id!r} tenant={self.tenant_id!r}>"


class RunRecord(Base):
    """
    Screening run orchestrating evaluation of a batch of candidates for a specific job.
    """
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    summary_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["TenantRecord"] = relationship("TenantRecord", back_populates="runs")
    job: Mapped["JobRecord"] = relationship("JobRecord", back_populates="runs")
    matches: Mapped[List["MatchRecord"]] = relationship("MatchRecord", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<RunRecord id={self.id!r} job={self.job_id!r} status={self.status!r}>"


class MatchRecord(Base):
    """
    Scored match between a candidate and a job in a given run.
    Contains overall score (0-100), subscores, plain language rationale, and critic status.
    """
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    subscores_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    critic_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pass")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationships
    candidate: Mapped["CandidateRecord"] = relationship("CandidateRecord", back_populates="matches")
    run: Mapped["RunRecord"] = relationship("RunRecord", back_populates="matches")
    decisions: Mapped[List["DecisionRecord"]] = relationship("DecisionRecord", back_populates="match", cascade="all, delete-orphan")

    @property
    def subscores(self) -> Dict[str, Any]:
        return json.loads(self.subscores_json) if self.subscores_json else {}

    @subscores.setter
    def subscores(self, val: Dict[str, Any]) -> None:
        self.subscores_json = json.dumps(val) if val is not None else None

    def __repr__(self) -> str:
        return f"<MatchRecord id={self.id!r} candidate={self.candidate_id!r} score={self.score}>"


class DecisionRecord(Base):
    """
    Human recruiter decision (approve, reject, hold) with mandatory human reasoning.
    The system never decides autonomously; human in the loop is mandatory.
    """
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)  # approve, reject, hold
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationship
    match: Mapped["MatchRecord"] = relationship("MatchRecord", back_populates="decisions")

    def __repr__(self) -> str:
        return f"<DecisionRecord id={self.id!r} decision={self.decision!r}>"


class AuditLogRecord(Base):
    """
    Immutable audit log entry recording every action with trace ID and tenant context.
    """
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    @property
    def payload(self) -> Dict[str, Any]:
        return json.loads(self.payload_json) if self.payload_json else {}

    @payload.setter
    def payload(self, val: Dict[str, Any]) -> None:
        self.payload_json = json.dumps(val) if val is not None else None

    def __repr__(self) -> str:
        return f"<AuditLogRecord id={self.id!r} action={self.action!r} trace={self.trace_id!r}>"


# ── Employee record (Strictly separated from Candidate Applicants) ───────────

class EmployeeRecord(Base):
    """
    Dedicated Employee entity representing active internal company staff.
    Kept strictly isolated from candidate applicants (candidates table)
    so deleting employees never impacts applicant resumes or screening runs.
    """
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="default", index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    designation: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    joining_date: Mapped[str] = mapped_column(String(32), nullable=False)
    skills_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    experience_years: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    resume_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resume_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    routine_work: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    @property
    def skills(self) -> List[str]:
        return json.loads(self.skills_json) if self.skills_json else []

    @skills.setter
    def skills(self, val: List[str]) -> None:
        self.skills_json = json.dumps(val) if val is not None else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "email": self.email,
            "department": self.department,
            "designation": self.designation,
            "joining_date": self.joining_date,
            "skills": self.skills,
            "experience_years": self.experience_years,
            "resume_filename": self.resume_filename,
            "resume_text": self.resume_text,
            "has_resume": bool(self.resume_text or self.resume_filename),
            "routine_work": self.routine_work or "General departmental engineering and operational tasks.",
            "status": self.status,
            "phone": self.phone,
            "location": self.location,
            "notes": self.notes,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<EmployeeRecord id={self.id!r} emp_id={self.employee_id!r} name={self.name!r}>"

