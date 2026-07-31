"""Checkpoints do LangGraph (Fase 2 do roadmap).

Preferência: PostgresSaver (estado sobrevive a reinício — critério de sucesso 31).
Fallback: MemorySaver para desenvolvimento sem a dependência opcional.
"""
from orchestrator.config import config


def build_checkpointer():
    try:
        from langgraph.checkpoint.postgres import PostgresSaver  # type: ignore
        from psycopg import Connection  # type: ignore

        dsn = config.database_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = Connection.connect(dsn, autocommit=True)
        saver = PostgresSaver(conn)
        saver.setup()
        return saver
    except Exception:  # noqa: BLE001
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()
