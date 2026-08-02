from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models import AgentDefinition, User
from app.schemas.api import AgentOut, AgentTestRequest, AgentUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/agents", tags=["agents"])

# Template base compartilhado (agents/prompts/base.txt), copiado para a imagem
# do backend. Exibido na tela como ponto de partida para customização.
BASE_PROMPT_PATH = Path("/app/agents/prompts/base.txt")
_LOCAL_BASE_PROMPT_PATH = (
    Path(__file__).resolve().parents[4] / "agents" / "prompts" / "base.txt"
)

# Placeholders que o runtime substitui ao montar o prompt, espelha
# agents/runtime/executor.PROMPT_PLACEHOLDERS.
PROMPT_PLACEHOLDERS = [
    "agent_name",
    "agent_version",
    "objective",
    "responsibilities",
    "input_manifest",
    "constraints",
    "allowed_tools",
    "quality_gates",
]

# Campos obrigatórios do contrato de agente (seção 11.2), espelha
# agents/registry.REQUIRED_FIELDS. Validados aqui para impedir que a tela de
# configuração salve uma definição que quebraria a execução no worker.
REQUIRED_CONFIG_FIELDS = [
    "id",
    "name",
    "version",
    "domain",
    "objective",
    "inputs",
    "outputs",
    "tools",
    "model",
    "quality_gates",
    "retry",
    "escalation",
]


def _to_out(agent: AgentDefinition) -> AgentOut:
    return AgentOut(
        id=agent.id,
        name=agent.name,
        version=agent.version,
        domain=agent.domain,
        configuration=agent.configuration or {},
        enabled=agent.enabled,
        stages=agent.stages or [],
        customized=(agent.configuration or {}) != (agent.default_configuration or {}),
    )


async def _validate_mcp_servers(db: AsyncSession, names: list[str]) -> None:
    """Impede vincular o agente a um servidor MCP inexistente (erro de digitação
    silencioso levaria a uma ferramenta simplesmente indisponível na fase 2)."""
    from app.models import McpServer

    known = {
        row for row in (await db.execute(select(McpServer.name))).scalars()
    }
    unknown = sorted(set(names) - known)
    if unknown:
        raise HTTPException(422, f"Servidores MCP inexistentes: {unknown}")


def _validate_configuration(configuration: dict) -> None:
    missing = [f for f in REQUIRED_CONFIG_FIELDS if f not in configuration]
    if missing:
        raise HTTPException(422, f"Configuração sem campos obrigatórios: {missing}")
    inputs = configuration.get("inputs") or {}
    tools = configuration.get("tools") or {}
    outputs = configuration.get("outputs") or {}
    if "required" not in inputs:
        raise HTTPException(422, "inputs.required ausente")
    if "allowed" not in tools or "denied" not in tools:
        raise HTTPException(422, "tools.allowed/denied ausentes")
    if "schema" not in outputs:
        raise HTTPException(422, "outputs.schema ausente")


@router.get("/prompt-template")
async def base_prompt_template(user: User = Depends(get_current_user)) -> dict:
    """Template base do prompt e placeholders disponíveis para customização."""
    for path in (BASE_PROMPT_PATH, _LOCAL_BASE_PROMPT_PATH):
        try:
            return {
                "template": path.read_text(encoding="utf-8"),
                "placeholders": PROMPT_PLACEHOLDERS,
            }
        except OSError:
            continue
    return {"template": "", "placeholders": PROMPT_PLACEHOLDERS}


@router.get("", response_model=list[AgentOut])
async def list_agents(
    domain: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AgentOut]:
    query = select(AgentDefinition).order_by(AgentDefinition.id)
    if domain:
        query = query.where(AgentDefinition.domain == domain)
    return [_to_out(a) for a in (await db.execute(query)).scalars()]


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(
    agent_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> AgentOut:
    agent = await db.get(AgentDefinition, agent_id)
    if agent is None:
        raise HTTPException(404, "Agente não encontrado")
    return _to_out(agent)


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: str,
    body: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("FACTORY_MANAGER")),
) -> AgentOut:
    agent = await db.get(AgentDefinition, agent_id)
    if agent is None:
        raise HTTPException(404, "Agente não encontrado")

    before = {"enabled": agent.enabled, "configuration": agent.configuration}

    configuration = dict(agent.configuration or {})
    if body.configuration is not None:
        configuration = dict(body.configuration)
    # Atalhos de edição parcial, aplicados sobre a configuração resultante.
    for field in ("objective", "responsibilities", "model", "tools", "quality_gates"):
        value = getattr(body, field)
        if value is not None:
            configuration[field] = value
    if body.mcp_servers is not None:
        configuration["mcp_servers"] = body.mcp_servers
    if configuration.get("mcp_servers"):
        await _validate_mcp_servers(db, configuration["mcp_servers"])
    if body.prompt_template is not None:
        # String vazia remove o prompt customizado (volta ao template base).
        if body.prompt_template.strip():
            configuration["prompt_template"] = body.prompt_template
        else:
            configuration.pop("prompt_template", None)

    if configuration != (agent.configuration or {}):
        _validate_configuration(configuration)
        agent.configuration = configuration
    if body.enabled is not None:
        agent.enabled = body.enabled

    await record_audit(
        db,
        event_type="config.changed",
        actor_type="human",
        actor_id=user.username,
        entity_type="agent_definition",
        entity_id=agent.id,
        before_state=before,
        after_state={"enabled": agent.enabled, "configuration": agent.configuration},
    )
    await db.commit()
    await db.refresh(agent)
    return _to_out(agent)


@router.post("/{agent_id}/reset", response_model=AgentOut)
async def reset_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("FACTORY_MANAGER")),
) -> AgentOut:
    """Restaura a configuração padrão (snapshot do YAML em agents/definitions)."""
    agent = await db.get(AgentDefinition, agent_id)
    if agent is None:
        raise HTTPException(404, "Agente não encontrado")
    if not agent.default_configuration:
        raise HTTPException(409, "Agente sem configuração padrão registrada")
    before = {"enabled": agent.enabled, "configuration": agent.configuration}
    agent.configuration = dict(agent.default_configuration)
    agent.enabled = True
    await record_audit(
        db,
        event_type="config.changed",
        actor_type="human",
        actor_id=user.username,
        entity_type="agent_definition",
        entity_id=agent.id,
        before_state=before,
        after_state={"enabled": True, "configuration": agent.configuration, "reset": True},
    )
    await db.commit()
    await db.refresh(agent)
    return _to_out(agent)


@router.post("/{agent_id}/test")
async def test_agent(
    agent_id: str,
    body: AgentTestRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("DEVELOPER")),
) -> dict:
    """Execução de teste do agente (dry-run): valida definição e monta o prompt."""
    agent = await db.get(AgentDefinition, agent_id)
    if agent is None:
        raise HTTPException(404, "Agente não encontrado")
    if not agent.enabled:
        raise HTTPException(409, "Agente desabilitado")
    config = agent.configuration or {}
    missing = [
        key
        for key in config.get("inputs", {}).get("required", [])
        if key not in body.input
    ]
    return {
        "agent_id": agent.id,
        "valid": not missing,
        "missing_required_inputs": missing,
        "model": config.get("model", {}),
        "allowed_tools": config.get("tools", {}).get("allowed", []),
        "uses_custom_prompt": bool((config.get("prompt_template") or "").strip()),
    }
