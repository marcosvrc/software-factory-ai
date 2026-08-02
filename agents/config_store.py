"""Configuração efetiva dos agentes vinda do banco (fonte de verdade viva).

Motivação: antes, orquestrador e workers carregavam a definição do agente
exclusivamente dos YAMLs em agents/definitions (AgentRegistry.load_default),
de modo que a tabela `agent_definitions` — e portanto a API/tela de
configuração — era puramente decorativa: desabilitar um agente ou editar seu
prompt/modelo não tinha nenhum efeito real na execução.

Este módulo lê a configuração efetiva do banco e a mescla sobre o YAML base
(YAML como semente/fallback). Há cache curto em memória para não consultar o
banco a cada tarefa; a janela de cache define o tempo máximo até uma mudança
feita na tela passar a valer para novas execuções.
"""
import os
import time

from sqlalchemy import MetaData, Table, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from shared.logging import get_logger

logger = get_logger("agents.config_store")

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://factory:factory@postgres:5432/factory"
)
CACHE_TTL_SECONDS = float(os.getenv("AGENT_CONFIG_CACHE_TTL_SECONDS", "10"))

_engine: AsyncEngine | None = None
_metadata = MetaData()
_table: Table | None = None
_cache: dict[str, dict] | None = None
_cache_at: float = 0.0


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, pool_size=2, max_overflow=2)
    return _engine


async def _get_table() -> Table:
    global _table
    if _table is None:
        async with _get_engine().connect() as conn:
            await conn.run_sync(
                lambda sync: _metadata.reflect(bind=sync, only=["agent_definitions"])
            )
        _table = _metadata.tables["agent_definitions"]
    return _table


def invalidate_cache() -> None:
    global _cache, _cache_at
    _cache = None
    _cache_at = 0.0


async def load_effective_configs(force: bool = False) -> dict[str, dict]:
    """Retorna {agent_id: {"enabled": bool, "configuration": dict}}.

    Em caso de falha de banco retorna {} (sem override), para que a execução
    continue com o YAML base em vez de quebrar o pipeline inteiro.
    """
    global _cache, _cache_at
    if not force and _cache is not None and (time.monotonic() - _cache_at) < CACHE_TTL_SECONDS:
        return _cache
    try:
        agents = await _get_table()
        async with _get_engine().connect() as conn:
            rows = (
                await conn.execute(
                    select(agents.c.id, agents.c.enabled, agents.c.configuration)
                )
            ).all()
        _cache = {
            row[0]: {"enabled": bool(row[1]), "configuration": row[2] or {}} for row in rows
        }
        _cache_at = time.monotonic()
        return _cache
    except SQLAlchemyError:
        logger.warning("agent_config_load_failed_using_yaml_defaults")
        return {}


async def effective_definition(base_definition: dict | None, agent_id: str) -> dict | None:
    """Mescla a configuração do banco sobre a definição YAML base."""
    overrides = await load_effective_configs()
    return merge_definition(base_definition, overrides.get(agent_id))


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def merge_definition(base_definition: dict | None, override: dict | None) -> dict | None:
    """Aplica a configuração do banco sobre o YAML base.

    - a configuração do banco vence campo a campo (merge profundo), pois é a
      edição explícita do usuário;
    - `enabled` vem sempre da coluna dedicada do banco, nunca do YAML, para
      que o toggle da tela tenha efeito real;
    - se o resultado ficar inválido (ex.: usuário removeu um campo
      obrigatório), cai para o YAML base em vez de derrubar a execução.
    """
    if override is None:
        return base_definition

    config = override.get("configuration") or {}
    enabled = override.get("enabled", True)

    if base_definition is None:
        # Agente existe só no banco (sem YAML correspondente): usa o que houver.
        merged = dict(config)
    else:
        merged = _deep_merge(base_definition, config)
    merged["enabled"] = enabled

    from agents.registry import validate_definition
    from shared.exceptions import AgentDefinitionError

    try:
        validate_definition(merged)
    except AgentDefinitionError as exc:
        logger.warning(
            f"agent_config_invalid_falling_back agent_id={merged.get('id', '?')} error={exc}"
        )
        if base_definition is None:
            return None
        fallback = dict(base_definition)
        fallback["enabled"] = enabled
        return fallback
    return merged
