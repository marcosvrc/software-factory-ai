"""Entidades principais (seção 12 da proposta) + usuários locais (seção 20.1)."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False)
    repository_url: Mapped[str | None] = mapped_column(String(1024))
    workspace_path: Mapped[str | None] = mapped_column(String(1024))

    demands: Mapped[list["Demand"]] = relationship(back_populates="project")
    runs: Mapped[list["WorkflowRun"]] = relationship(back_populates="project")


class Demand(TimestampMixin, Base):
    __tablename__ = "demands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    requester: Mapped[str | None] = mapped_column(String(255))
    business_value: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="CREATED", nullable=False)

    project: Mapped["Project"] = relationship(back_populates="demands")
    runs: Mapped[list["WorkflowRun"]] = relationship(back_populates="demand")


class WorkflowRun(TimestampMixin, Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    demand_id: Mapped[str] = mapped_column(ForeignKey("demands.id"), nullable=False)
    graph_version: Mapped[str] = mapped_column(String(64), default="software_delivery@1.0.0")
    status: Mapped[str] = mapped_column(String(32), default="CREATED", nullable=False)
    current_node: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[str] = mapped_column(String(36), default=_uuid, index=True)

    project: Mapped["Project"] = relationship(back_populates="runs")
    demand: Mapped["Demand"] = relationship(back_populates="runs")
    tasks: Mapped[list["Task"]] = relationship(back_populates="workflow_run")


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow_run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False)
    parent_task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"))
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    assigned_agent_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="BACKLOG", nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    priority: Mapped[int] = mapped_column(Integer, default=5)

    workflow_run: Mapped["WorkflowRun"] = relationship(back_populates="tasks")


class AgentDefinition(TimestampMixin, Base):
    __tablename__ = "agent_definitions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AgentExecution(TimestampMixin, Base):
    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128))
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="RUNNING")
    input_reference: Mapped[str | None] = mapped_column(String(1024))
    output_reference: Mapped[str | None] = mapped_column(String(1024))
    token_usage: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(128))


class Artifact(TimestampMixin, Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    workflow_run_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_runs.id"))
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"))
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str | None] = mapped_column(String(128))


class Finding(TimestampMixin, Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    agent_execution_id: Mapped[str | None] = mapped_column(ForeignKey("agent_executions.id"))
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    recommendation: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="OPEN")


class Decision(TimestampMixin, Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow_run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"))
    decision_type: Mapped[str] = mapped_column(String(64), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    options_considered: Mapped[list] = mapped_column(JSON, default=list)
    selected_option: Mapped[str | None] = mapped_column(String(255))
    decided_by: Mapped[str | None] = mapped_column(String(128))


class Approval(TimestampMixin, Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow_run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"))
    approval_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="REQUESTED")
    requested_from: Mapped[str | None] = mapped_column(String(128))
    decided_by: Mapped[str | None] = mapped_column(String(128))
    rationale: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    impacts: Mapped[list] = mapped_column(JSON, default=list)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    alternatives: Mapped[list] = mapped_column(JSON, default=list)
    recommendation: Mapped[str | None] = mapped_column(Text)
    artifacts: Mapped[list] = mapped_column(JSON, default=list)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    """Trilha de auditoria append-only (seções 12, 20.5 e 25)."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    correlation_id: Mapped[str | None] = mapped_column(String(36), index=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    before_state: Mapped[dict | None] = mapped_column(JSON)
    after_state: Mapped[dict | None] = mapped_column(JSON)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_execution_id: Mapped[str] = mapped_column(
        ForeignKey("agent_executions.id"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    input_hash: Mapped[str | None] = mapped_column(String(64))
    output_reference: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(32), default="RUNNING")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Risk(TimestampMixin, Base):
    __tablename__ = "risks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    probability: Mapped[float] = mapped_column(Float, default=0.5)
    impact: Mapped[float] = mapped_column(Float, default=0.5)
    score: Mapped[float] = mapped_column(Float, default=0.25)
    owner: Mapped[str | None] = mapped_column(String(128))
    mitigation: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="OPEN")


class User(TimestampMixin, Base):
    """Usuários locais (seção 20.1): senhas Argon2id, papéis da seção 20.2."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="VIEWER", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    refresh_token_hash: Mapped[str | None] = mapped_column(String(512))
