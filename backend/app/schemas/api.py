"""Schemas de entrada/saída da API (Pydantic 2)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Projetos ---
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    repository_url: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    repository_url: str | None = None


class ProjectOut(ORMModel):
    id: str
    name: str
    description: str | None
    status: str
    repository_url: str | None
    workspace_path: str | None
    created_at: datetime
    updated_at: datetime


# --- Demandas ---
class DemandCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: int = Field(default=5, ge=1, le=10)
    requester: str | None = None
    business_value: str | None = None


class DemandOut(ORMModel):
    id: str
    project_id: str
    title: str
    description: str | None
    priority: int
    requester: str | None
    business_value: str | None
    status: str
    created_at: datetime


# --- Workflow runs ---
class RunOut(ORMModel):
    id: str
    project_id: str
    demand_id: str
    graph_version: str
    status: str
    current_node: str | None
    started_at: datetime | None
    finished_at: datetime | None
    correlation_id: str
    created_at: datetime


class TaskOut(ORMModel):
    id: str
    workflow_run_id: str
    parent_task_id: str | None
    type: str
    title: str
    description: str | None
    assigned_agent_id: str | None
    status: str
    attempt: int
    max_attempts: int
    priority: int
    created_at: datetime
    updated_at: datetime


# --- Aprovações ---
class ApprovalDecision(BaseModel):
    rationale: str | None = None


class ApprovalOut(ORMModel):
    id: str
    workflow_run_id: str
    task_id: str | None
    approval_type: str
    status: str
    requested_from: str | None
    decided_by: str | None
    rationale: str | None
    summary: str | None
    impacts: list
    risks: list
    alternatives: list
    recommendation: str | None
    artifacts: list
    requested_at: datetime
    decided_at: datetime | None


# --- Artefatos ---
class ArtifactOut(ORMModel):
    id: str
    project_id: str
    workflow_run_id: str | None
    task_id: str | None
    type: str
    name: str
    storage_key: str
    checksum: str | None
    version: int
    created_by: str | None
    created_at: datetime


# --- Agentes ---
class AgentOut(ORMModel):
    id: str
    name: str
    version: str
    domain: str
    configuration: dict
    enabled: bool


class AgentUpdate(BaseModel):
    enabled: bool | None = None
    configuration: dict | None = None


class AgentTestRequest(BaseModel):
    input: dict = Field(default_factory=dict)


# --- Auth ---
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class TimelineEntry(BaseModel):
    timestamp: datetime
    event_type: str
    actor_type: str | None = None
    actor_id: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    metadata: dict | None = None
