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
    demand_title: str | None = None
    project_name: str | None = None


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
    stages: list = Field(default_factory=list)
    # True quando a configuração efetiva difere do padrão do YAML (permite a
    # UI sinalizar "customizado" e oferecer "restaurar padrão").
    customized: bool = False


class AgentUpdate(BaseModel):
    """Atualização parcial da configuração do agente.

    `configuration` substitui a configuração efetiva por inteiro (a tela envia
    o objeto completo já editado). Os demais campos são atalhos para editar
    apenas uma parte, aplicados sobre a configuração atual.
    """

    enabled: bool | None = None
    configuration: dict | None = None
    prompt_template: str | None = None
    objective: str | None = None
    responsibilities: list[str] | None = None
    model: dict | None = None
    tools: dict | None = None
    quality_gates: list[str] | None = None
    # Nomes de servidores MCP que este agente pode usar (fase 2 do MCP).
    mcp_servers: list[str] | None = None


class AgentTestRequest(BaseModel):
    input: dict = Field(default_factory=dict)


# --- Servidores MCP ---
class McpServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    transport: str = Field(default="stdio", pattern="^(stdio|http)$")
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    enabled: bool = False


class McpServerUpdate(BaseModel):
    description: str | None = None
    transport: str | None = Field(default=None, pattern="^(stdio|http)$")
    command: str | None = None
    args: list[str] | None = None
    # Ausente = mantém os valores atuais; enviado = substitui por completo.
    env: dict[str, str] | None = None
    headers: dict[str, str] | None = None
    url: str | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    enabled: bool | None = None


class McpToolOut(BaseModel):
    name: str
    description: str = ""
    input_schema: dict = Field(default_factory=dict)


class McpServerOut(ORMModel):
    id: str
    name: str
    description: str | None
    transport: str
    command: str | None
    args: list
    url: str | None
    timeout_seconds: int
    enabled: bool
    tools: list
    last_status: str | None
    last_error: str | None
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # Chaves de env/headers são expostas (úteis para conferência), mas os
    # valores nunca — podem conter tokens de acesso.
    env_keys: list[str] = Field(default_factory=list)
    header_keys: list[str] = Field(default_factory=list)
    # Agentes que declararam usar este servidor.
    used_by_agents: list[str] = Field(default_factory=list)
    # Estado da autorização OAuth (tokens nunca são expostos):
    # not_applicable | not_authorized | authorized | expired
    auth_status: str = "not_applicable"
    oauth_expires_at: datetime | None = None
    oauth_scope: str | None = None
    has_oauth_client: bool = False


class McpOAuthStartOut(BaseModel):
    authorization_url: str
    redirect_uri: str


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
