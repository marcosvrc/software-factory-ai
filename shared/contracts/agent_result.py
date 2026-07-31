"""Contratos de saída estruturada dos agentes (seção 11.3 da proposta)."""
from pydantic import BaseModel, Field
from typing import Literal


class Finding(BaseModel):
    id: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    category: str
    description: str
    evidence: list[str]
    recommendation: str


class AgentResult(BaseModel):
    agent_id: str
    execution_id: str
    status: Literal["approved", "changes_requested", "blocked", "failed"]
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    next_recommended_agents: list[str] = Field(default_factory=list)
