"""Ponto de entrada do orquestrador.

Responsabilidades (seção 7.1): receber demandas, criar plano, escolher agentes,
controlar estados, verificar quality gates, limitar ciclos, solicitar
aprovações e consolidar resultados.

Descobre execuções QUEUED/RETRYING no PostgreSQL (fonte de verdade) e também
reage a eventos `workflow.run.requested` no RabbitMQ.
"""
import asyncio
import json

import aio_pika
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from agents.registry import AgentRegistry
from orchestrator import db
from orchestrator.checkpoints.saver import build_checkpointer
from orchestrator.config import config
from orchestrator.graphs.software_delivery import build_graph
from orchestrator.routing.router import STAGE_AGENTS
from shared.logging import configure_logging, get_logger

logger = get_logger("orchestrator.main")

EVENTS_EXCHANGE = "factory.events"
ORCHESTRATOR_QUEUE = "factory.orchestrator"

_running: set[str] = set()
_checkpointer = None  # inicializado em main(); com checkpointer, ainvoke(None,
# config) retoma exatamente do nó onde a execução parou (ver
# orchestrator/checkpoints/saver.py), em vez de recomeçar do zero após um
# restart do orchestrator ou uma queda momentânea do Postgres.

# Falhas transitórias de conexão (Postgres em recovery, rede momentaneamente
# indisponível) não devem fazer a run ficar presa em RUNNING para sempre:
# tenta gravar o status de falha algumas vezes com backoff antes de desistir.
_retry_on_db_error = retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=15),
    reraise=True,
)


@_retry_on_db_error
async def _mark_run_status(run_id: str, **values) -> None:
    await db.update_run(run_id, **values)


async def run_workflow(run: dict, *, resume: bool = False) -> None:
    run_id = run["workflow_run_id"]
    if run_id in _running:
        return
    _running.add(run_id)
    graph = build_graph(checkpointer=_checkpointer)
    graph_config = {"configurable": {"thread_id": run_id}, "recursion_limit": 100}
    try:
        await _mark_run_status(run_id, status="RUNNING")
        # Só retoma com None se de fato existir um checkpoint salvo para este
        # thread_id. Sem essa verificação, ainvoke(None, ...) falha com
        # EmptyInputError quando o checkpointer é o MemorySaver de fallback
        # (perdeu tudo ao reiniciar) ou quando a run nunca chegou a executar
        # nenhum nó — nesses casos é preciso recomeçar do zero.
        existing_checkpoint = resume and await _checkpointer.aget_tuple(graph_config)
        if existing_checkpoint:
            invoke_input = None
        else:
            invoke_input = {
                **run,
                "stage_results": {},
                "artifacts": [],
                "code_files": [],
                "findings_by_stage": {},
                "decisions": [],
                "cycles": {},
            }
        final_state = await graph.ainvoke(invoke_input, config=graph_config)
        if final_state.get("current_stage") == "delivered":
            await _mark_run_status(run_id, status="COMPLETED", finished_at=db.now())
            await db.record_audit_event(
                event_type="workflow.completed",
                entity_type="workflow_run",
                entity_id=run_id,
                correlation_id=run["correlation_id"],
            )
        else:
            await _mark_run_status(run_id, status="CANCELLED", finished_at=db.now())
    except Exception as exc:  # noqa: BLE001
        logger.exception("workflow_failed")
        try:
            await _mark_run_status(run_id, status="FAILED_RETRYABLE", finished_at=db.now())
            await db.record_audit_event(
                event_type="workflow.failed",
                entity_type="workflow_run",
                entity_id=run_id,
                correlation_id=run.get("correlation_id"),
                metadata_={"error": str(exc)[:500]},
            )
        except Exception:  # noqa: BLE001
            # Mesmo após as tentativas de retry, não foi possível persistir o
            # status de falha (ex.: Postgres ainda em recovery). A run fica
            # presa em RUNNING no banco, mas o polling (poll_database) vai
            # tentar retomá-la com checkpoint na próxima iteração assim que
            # o banco voltar — ver _reconcile_stale_running_runs.
            logger.exception("workflow_failed_status_update_also_failed")
    finally:
        _running.discard(run_id)


async def _reconcile_stale_running_runs() -> None:
    """Recupera runs presas em RUNNING sem um worker local ativo.

    Isso acontece quando o processo do orchestrator reinicia (deploy, crash)
    ou quando o Postgres cai no meio de uma execução e nem o próprio
    tratamento de erro consegue persistir o status de falha (ver
    run_workflow). Sem isso, a run fica congelada em RUNNING para sempre e
    precisa de intervenção manual no banco.
    """
    try:
        for run in await db.fetch_stale_running_runs():
            run_id = run["workflow_run_id"]
            if run_id in _running:
                continue
            logger.warning(f"resuming_stale_run run_id={run_id}")
            asyncio.create_task(run_workflow(run, resume=True))
    except Exception:  # noqa: BLE001
        logger.exception("reconcile_error")


async def poll_database() -> None:
    while True:
        try:
            for run in await db.fetch_queued_runs():
                if run["workflow_run_id"] not in _running:
                    asyncio.create_task(run_workflow(run))
        except Exception:  # noqa: BLE001
            logger.exception("poll_error")
        await _reconcile_stale_running_runs()
        await asyncio.sleep(5)


async def consume_events() -> None:
    while True:
        try:
            connection = await aio_pika.connect_robust(config.rabbitmq_url)
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                EVENTS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
            )
            queue = await channel.declare_queue(ORCHESTRATOR_QUEUE, durable=True)
            await queue.bind(exchange, routing_key="workflow.#")
            await queue.bind(exchange, routing_key="approval.#")
            async with queue.iterator() as iterator:
                async for message in iterator:
                    async with message.process():
                        payload = json.loads(message.body)
                        logger.info(
                            "event_received", extra={"correlation_id": payload.get("correlation_id")}
                        )
        except Exception:  # noqa: BLE001
            logger.exception("event_consumer_error")
            await asyncio.sleep(5)


async def sync_agents() -> None:
    """Publica os YAMLs de agents/definitions no banco (default + metadados).

    Não sobrescreve a configuração efetiva de agentes já existentes: ver
    db.sync_agent_definitions. Também publica em que etapas do pipeline cada
    agente participa (STAGE_AGENTS), consumido pela tela de configuração.
    """
    registry = AgentRegistry.load_default()
    stages_by_agent: dict[str, list[str]] = {}
    for stage, agent_ids in STAGE_AGENTS.items():
        for agent_id in agent_ids:
            stages_by_agent.setdefault(agent_id, []).append(stage)
    definitions = [
        {
            "id": d["id"],
            "name": d["name"],
            "version": d.get("version", "1.0.0"),
            "domain": d["domain"],
            "configuration": d,
            "stages": stages_by_agent.get(d["id"], []),
        }
        for d in registry.all()
    ]
    await db.sync_agent_definitions(definitions)
    logger.info(f"agent_definitions_synced total={len(definitions)}")


async def main() -> None:
    global _checkpointer
    configure_logging()
    logger.info("orchestrator_starting")
    for attempt in range(30):
        try:
            await sync_agents()
            break
        except Exception:  # noqa: BLE001
            logger.warning(f"waiting_for_database attempt={attempt}")
            await asyncio.sleep(5)
    _checkpointer = await build_checkpointer()
    await asyncio.gather(poll_database(), consume_events())


if __name__ == "__main__":
    asyncio.run(main())
