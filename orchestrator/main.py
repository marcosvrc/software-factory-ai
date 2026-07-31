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

from agents.registry import AgentRegistry
from orchestrator import db
from orchestrator.config import config
from orchestrator.graphs.software_delivery import build_graph
from shared.logging import configure_logging, get_logger

logger = get_logger("orchestrator.main")

EVENTS_EXCHANGE = "factory.events"
ORCHESTRATOR_QUEUE = "factory.orchestrator"

_running: set[str] = set()


async def run_workflow(run: dict) -> None:
    run_id = run["workflow_run_id"]
    if run_id in _running:
        return
    _running.add(run_id)
    graph = build_graph()
    try:
        await db.update_run(run_id, status="RUNNING")
        state = {
            **run,
            "stage_results": {},
            "artifacts": [],
            "findings": [],
            "decisions": [],
            "cycles": {},
        }
        final_state = await graph.ainvoke(
            state, config={"configurable": {"thread_id": run_id}, "recursion_limit": 100}
        )
        if final_state.get("current_stage") == "delivered":
            await db.update_run(run_id, status="COMPLETED", finished_at=db.now())
            await db.record_audit_event(
                event_type="workflow.completed",
                entity_type="workflow_run",
                entity_id=run_id,
                correlation_id=run["correlation_id"],
            )
        else:
            await db.update_run(run_id, status="CANCELLED", finished_at=db.now())
    except Exception as exc:  # noqa: BLE001
        logger.exception("workflow_failed")
        await db.update_run(run_id, status="FAILED_RETRYABLE", finished_at=db.now())
        await db.record_audit_event(
            event_type="workflow.failed",
            entity_type="workflow_run",
            entity_id=run_id,
            correlation_id=run.get("correlation_id"),
            metadata_={"error": str(exc)[:500]},
        )
    finally:
        _running.discard(run_id)


async def poll_database() -> None:
    while True:
        try:
            for run in await db.fetch_queued_runs():
                if run["workflow_run_id"] not in _running:
                    asyncio.create_task(run_workflow(run))
        except Exception:  # noqa: BLE001
            logger.exception("poll_error")
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
    registry = AgentRegistry.load_default()
    definitions = [
        {
            "id": d["id"],
            "name": d["name"],
            "version": d.get("version", "1.0.0"),
            "domain": d["domain"],
            "configuration": d,
        }
        for d in registry.all()
    ]
    await db.sync_agent_definitions(definitions)
    logger.info(f"agent_definitions_synced total={len(definitions)}")


async def main() -> None:
    configure_logging()
    logger.info("orchestrator_starting")
    for attempt in range(30):
        try:
            await sync_agents()
            break
        except Exception:  # noqa: BLE001
            logger.warning(f"waiting_for_database attempt={attempt}")
            await asyncio.sleep(5)
    await asyncio.gather(poll_database(), consume_events())


if __name__ == "__main__":
    asyncio.run(main())
