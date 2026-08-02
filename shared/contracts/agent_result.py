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


class CodeFile(BaseModel):
    """Conteúdo real de um arquivo de código criado/alterado pelo agente.

    Distinto de `AgentResult.artifacts` (que só lista nomes/paths como
    strings): aqui vai o CONTEÚDO completo do arquivo, para que seja
    persistido de fato (MinIO + tabela `artifacts`) e possa ser lido como
    contexto real por agentes subsequentes (code review, testes, etc.).
    """

    path: str
    content: str
    language: str | None = None


class AgentResult(BaseModel):
    agent_id: str
    execution_id: str
    status: Literal["approved", "changes_requested", "blocked", "failed"]
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    code_files: list[CodeFile] = Field(default_factory=list)
    next_recommended_agents: list[str] = Field(default_factory=list)
