from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models import AgentDefinition, User
from app.schemas.api import AgentOut, AgentTestRequest, AgentUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
async def list_agents(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[AgentDefinition]:
    return list((await db.execute(select(AgentDefinition).order_by(AgentDefinition.id))).scalars())


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(
    agent_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> AgentDefinition:
    agent = await db.get(AgentDefinition, agent_id)
    if agent is None:
        raise HTTPException(404, "Agente não encontrado")
    return agent


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: str,
    body: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("FACTORY_MANAGER")),
) -> AgentDefinition:
    agent = await db.get(AgentDefinition, agent_id)
    if agent is None:
        raise HTTPException(404, "Agente não encontrado")
    before = {"enabled": agent.enabled}
    if body.enabled is not None:
        agent.enabled = body.enabled
    if body.configuration is not None:
        agent.configuration = body.configuration
    await record_audit(
        db, event_type="config.changed", actor_type="human", actor_id=user.username,
        entity_type="agent_definition", entity_id=agent.id,
        before_state=before, after_state={"enabled": agent.enabled},
    )
    await db.commit()
    await db.refresh(agent)
    return agent


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
    }
