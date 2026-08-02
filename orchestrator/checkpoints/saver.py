"""Checkpoints do LangGraph (Fase 2 do roadmap).

Preferência: AsyncPostgresSaver (estado sobrevive a reinício do processo e a
quedas momentâneas do Postgres — critério de sucesso 31). Sem isso, qualquer
restart do orchestrator ou instabilidade de conexão durante uma execução em
andamento perde todo o progresso e o item precisa ser reprocessado do zero
(ver ADR sobre resiliência do orquestrador).

Fallback: MemorySaver, só usado se o Postgres estiver genuinamente
inalcançável na inicialização (ex.: ambiente de teste sem banco).
"""
from psycopg_pool import AsyncConnectionPool

from orchestrator.config import config
from shared.logging import get_logger

logger = get_logger("orchestrator.checkpoints")

# min_size=0: o pool não mantém conexões ociosas nem falha na criação se o
# Postgres estiver temporariamente fora; ele reconecta sob demanda a cada
# checkpoint, em vez de manter uma única conexão presa (psycopg.Connection
# simples) que morre para sempre na primeira queda do Postgres.
POOL_KWARGS = {"autocommit": True, "prepare_threshold": 0}


async def build_checkpointer():
    dsn = config.database_url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # type: ignore

        pool = AsyncConnectionPool(
            conninfo=dsn, kwargs=POOL_KWARGS, min_size=0, max_size=10, open=False
        )
        await pool.open(wait=True, timeout=30)
        saver = AsyncPostgresSaver(conn=pool)
        await saver.setup()
        logger.info("checkpointer_ready backend=postgres")
        return saver
    except Exception:  # noqa: BLE001
        logger.exception("checkpointer_postgres_unavailable_using_memory")
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()
