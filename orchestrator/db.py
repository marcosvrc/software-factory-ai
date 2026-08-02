"""Acesso do orquestrador ao PostgreSQL (fonte de verdade, princípio 3.3).

Usa SQLAlchemy Core sobre as tabelas criadas pelas migrations do backend.
"""
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import MetaData, Table, insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from orchestrator.config import config

engine: AsyncEngine = create_async_engine(config.database_url, pool_pre_ping=True)
metadata = MetaData()

_tables: dict[str, Table] = {}


async def table(name: str) -> Table:
    if name not in _tables:
        async with engine.connect() as conn:
            await conn.run_sync(lambda sync: metadata.reflect(bind=sync, only=[name]))
        _tables[name] = metadata.tables[name]
    return _tables[name]


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


async def create_task(
    *, workflow_run_id: str, type_: str, title: str, agent_id: str, priority: int = 5
) -> str:
    tasks = await table("tasks")
    task_id = new_id()
    async with engine.begin() as conn:
        await conn.execute(
            insert(tasks).values(
                id=task_id,
                workflow_run_id=workflow_run_id,
                type=type_,
                title=title,
                assigned_agent_id=agent_id,
                status="READY",
                attempt=0,
                max_attempts=3,
                priority=priority,
                created_at=now(),
                updated_at=now(),
            )
        )
    return task_id


async def get_task_status(task_id: str) -> str | None:
    tasks = await table("tasks")
    async with engine.connect() as conn:
        row = (await conn.execute(select(tasks.c.status).where(tasks.c.id == task_id))).first()
    return row[0] if row else None


async def update_run(run_id: str, **values) -> None:
    runs = await table("workflow_runs")
    values["updated_at"] = now()
    async with engine.begin() as conn:
        await conn.execute(update(runs).where(runs.c.id == run_id).values(**values))


async def record_audit_event(
    *,
    event_type: str,
    actor_type: str = "orchestrator",
    actor_id: str = "orchestrator",
    entity_type: str | None = None,
    entity_id: str | None = None,
    correlation_id: str | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    metadata_: dict | None = None,
) -> None:
    audit = await table("audit_events")
    async with engine.begin() as conn:
        await conn.execute(
            insert(audit).values(
                id=new_id(),
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                before_state=before_state,
                after_state=after_state,
                metadata=metadata_,
                created_at=now(),
            )
        )


async def create_approval(
    *,
    workflow_run_id: str,
    approval_type: str,
    summary: str,
    requested_from: str = "APPROVER",
    impacts: list | None = None,
    risks: list | None = None,
    alternatives: list | None = None,
    recommendation: str | None = None,
    artifacts: list | None = None,
) -> str:
    approvals = await table("approvals")
    approval_id = new_id()
    async with engine.begin() as conn:
        await conn.execute(
            insert(approvals).values(
                id=approval_id,
                workflow_run_id=workflow_run_id,
                approval_type=approval_type,
                status="REQUESTED",
                requested_from=requested_from,
                summary=summary,
                impacts=impacts or [],
                risks=risks or [],
                alternatives=alternatives or [],
                recommendation=recommendation,
                artifacts=artifacts or [],
                requested_at=now(),
                created_at=now(),
                updated_at=now(),
            )
        )
    return approval_id


async def get_approval_status(approval_id: str) -> str | None:
    approvals = await table("approvals")
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                select(approvals.c.status).where(approvals.c.id == approval_id)
            )
        ).first()
    return row[0] if row else None


async def get_approval_rationale(approval_id: str) -> str | None:
    """Retorna a justificativa registrada na decisão humana. Usada pelo gate
    de intake_analysis (orchestrator/nodes/approvals.intake_clarification)
    para capturar as respostas do solicitante às perguntas de esclarecimento
    e realimentá-las na próxima tentativa de análise."""
    approvals = await table("approvals")
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                select(approvals.c.rationale).where(approvals.c.id == approval_id)
            )
        ).first()
    return row[0] if row else None


async def record_decision(
    *, workflow_run_id: str, decision_type: str, rationale: str, selected_option: str,
    options_considered: list | None = None, decided_by: str = "orchestrator",
) -> None:
    decisions = await table("decisions")
    async with engine.begin() as conn:
        await conn.execute(
            insert(decisions).values(
                id=new_id(),
                workflow_run_id=workflow_run_id,
                decision_type=decision_type,
                rationale=rationale,
                options_considered=options_considered or [],
                selected_option=selected_option,
                decided_by=decided_by,
                created_at=now(),
                updated_at=now(),
            )
        )


async def fetch_queued_runs() -> list[dict]:
    runs = await table("workflow_runs")
    demands = await table("demands")
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                select(
                    runs.c.id,
                    runs.c.project_id,
                    runs.c.demand_id,
                    runs.c.correlation_id,
                    demands.c.title,
                    demands.c.description,
                )
                .join(demands, demands.c.id == runs.c.demand_id)
                .where(runs.c.status.in_(["QUEUED", "RETRYING"]))
            )
        ).all()
    return [
        {
            "workflow_run_id": r[0],
            "project_id": r[1],
            "demand_id": r[2],
            "correlation_id": r[3],
            "demand_title": r[4],
            "demand_description": r[5] or "",
        }
        for r in rows
    ]


# Runs em RUNNING ou WAITING_HUMAN sem atualização por mais que isso são
# consideradas órfãs (processo do orchestrator caiu ou perdeu a conexão com
# o banco no meio da execução, OU a tarefa local que fazia polling de uma
# aprovação humana (orchestrator/nodes/approvals._wait_for_approval) morreu
# junto com o processo — ver orchestrator/main.py
# _reconcile_stale_running_runs). O valor é maior que o intervalo de polling
# (5s) e maior que a duração típica de uma etapa (múltiplos agentes em
# paralelo, ~30s cada), para não roubar runs que só estão demoradas numa
# etapa longa: enquanto o processo original está vivo, `_running` no main.py
# já protege contra reprocessamento duplicado; isso só age quando o processo
# de fato reiniciou.
STALE_RUNNING_THRESHOLD_SECONDS = int(os.getenv("STALE_RUNNING_THRESHOLD_SECONDS", "180"))

# Status em que uma run pode ficar órfã: RUNNING (grafo processando etapas)
# ou WAITING_HUMAN (aguardando decisão de aprovação — a tarefa local que
# faz o polling dessa decisão também é perdida quando o processo reinicia).
_RESUMABLE_STATUSES = ("RUNNING", "WAITING_HUMAN")


async def fetch_stale_running_runs() -> list[dict]:
    runs = await table("workflow_runs")
    demands = await table("demands")
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                select(
                    runs.c.id,
                    runs.c.project_id,
                    runs.c.demand_id,
                    runs.c.correlation_id,
                    demands.c.title,
                    demands.c.description,
                )
                .join(demands, demands.c.id == runs.c.demand_id)
                .where(
                    runs.c.status.in_(_RESUMABLE_STATUSES),
                    runs.c.updated_at
                    < now() - timedelta(seconds=STALE_RUNNING_THRESHOLD_SECONDS),
                )
            )
        ).all()
    return [
        {
            "workflow_run_id": r[0],
            "project_id": r[1],
            "demand_id": r[2],
            "correlation_id": r[3],
            "demand_title": r[4],
            "demand_description": r[5] or "",
        }
        for r in rows
    ]


async def sync_agent_definitions(definitions: list[dict]) -> None:
    """Publica no banco as definições vindas dos YAMLs de agents/definitions.

    IMPORTANTE: a coluna `configuration` NUNCA é sobrescrita para agentes que
    já existem. Ela é a configuração efetiva, editável pelo usuário na tela de
    configuração de agentes; antes desta versão o sync a sobrescrevia a cada
    restart do orquestrador, apagando silenciosamente qualquer customização.
    O YAML é gravado apenas em `default_configuration` (usado para restaurar o
    padrão) e `stages`/metadados descritivos são atualizados normalmente.
    """
    agents = await table("agent_definitions")
    async with engine.begin() as conn:
        existing = {row[0] for row in (await conn.execute(select(agents.c.id))).all()}
        for d in definitions:
            if d["id"] in existing:
                await conn.execute(
                    update(agents)
                    .where(agents.c.id == d["id"])
                    .values(
                        name=d["name"],
                        version=d["version"],
                        domain=d["domain"],
                        default_configuration=d["configuration"],
                        stages=d.get("stages", []),
                        updated_at=now(),
                    )
                )
            else:
                await conn.execute(
                    insert(agents).values(
                        id=d["id"],
                        name=d["name"],
                        version=d["version"],
                        domain=d["domain"],
                        configuration=d["configuration"],
                        default_configuration=d["configuration"],
                        stages=d.get("stages", []),
                        enabled=True,
                        created_at=now(),
                        updated_at=now(),
                    )
                )
