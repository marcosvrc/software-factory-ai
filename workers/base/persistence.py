"""Persistência dos workers.

Workers alteram apenas o status de suas execuções e tarefas atribuídas
(regra 10.4); o estado global pertence ao orquestrador.
"""
import os
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import MetaData, Table, insert, update
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://factory:factory@postgres:5432/factory"
)

engine: AsyncEngine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
metadata = MetaData()
_tables: dict[str, Table] = {}


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


async def table(name: str) -> Table:
    if name not in _tables:
        async with engine.connect() as conn:
            await conn.run_sync(lambda sync: metadata.reflect(bind=sync, only=[name]))
        _tables[name] = metadata.tables[name]
    return _tables[name]


async def update_task_status(task_id: str, status: str, increment_attempt: bool = False) -> None:
    tasks = await table("tasks")
    values: dict = {"status": status, "updated_at": now()}
    async with engine.begin() as conn:
        if increment_attempt:
            from sqlalchemy import select

            row = (
                await conn.execute(select(tasks.c.attempt).where(tasks.c.id == task_id))
            ).first()
            values["attempt"] = (row[0] if row else 0) + 1
        await conn.execute(update(tasks).where(tasks.c.id == task_id).values(**values))


async def record_agent_execution(
    *,
    task_id: str,
    agent_id: str,
    model: str | None,
    status: str,
    input_reference: str | None,
    output_reference: str | None,
    token_usage: int,
    duration_ms: int,
    error_code: str | None = None,
) -> str:
    executions = await table("agent_executions")
    execution_id = new_id()
    async with engine.begin() as conn:
        await conn.execute(
            insert(executions).values(
                id=execution_id,
                task_id=task_id,
                agent_id=agent_id,
                model=model,
                prompt_version="base@1.0.0",
                status=status,
                input_reference=input_reference,
                output_reference=output_reference,
                token_usage=token_usage,
                duration_ms=duration_ms,
                error_code=error_code,
                created_at=now(),
                updated_at=now(),
            )
        )
    return execution_id


async def record_artifact(
    *,
    project_id: str | None,
    workflow_run_id: str,
    task_id: str,
    type_: str,
    name: str,
    storage_key: str,
    checksum: str | None,
    created_by: str | None,
) -> str:
    """Registra um artefato de primeira classe (tabela `artifacts`), visível
    na API (/runs/{id}/artifacts) e no frontend. Sem isso, artefatos ficam
    só como objetos "soltos" no MinIO, sem rastreabilidade estruturada."""
    artifacts = await table("artifacts")
    artifact_id = new_id()
    async with engine.begin() as conn:
        await conn.execute(
            insert(artifacts).values(
                id=artifact_id,
                project_id=project_id,
                workflow_run_id=workflow_run_id,
                task_id=task_id,
                type=type_,
                name=name,
                storage_key=storage_key,
                checksum=checksum,
                version=1,
                created_by=created_by,
                created_at=now(),
                updated_at=now(),
            )
        )
    return artifact_id


async def record_findings(task_id: str, execution_id: str, findings: list[dict]) -> None:
    if not findings:
        return
    table_ = await table("findings")
    async with engine.begin() as conn:
        for f in findings:
            await conn.execute(
                insert(table_).values(
                    id=new_id(),
                    task_id=task_id,
                    agent_execution_id=execution_id,
                    category=f.get("category", "general"),
                    severity=f.get("severity", "info"),
                    description=f.get("description", ""),
                    evidence=f.get("evidence", []),
                    recommendation=f.get("recommendation", ""),
                    status="OPEN",
                    created_at=now(),
                    updated_at=now(),
                )
            )


async def record_audit_event(
    *, event_type: str, actor_id: str, entity_type: str, entity_id: str,
    correlation_id: str | None, metadata_: dict | None = None,
) -> None:
    audit = await table("audit_events")
    async with engine.begin() as conn:
        await conn.execute(
            insert(audit).values(
                id=new_id(),
                event_type=event_type,
                actor_type="agent",
                actor_id=actor_id,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                metadata=metadata_,
                created_at=now(),
            )
        )
