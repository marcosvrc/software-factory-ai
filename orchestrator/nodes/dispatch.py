"""Despacho de tarefas para workers via RabbitMQ e coleta de resultados.

O worker persiste o AgentResult no Redis (chave task_result:{task_id}) e
atualiza o status da tarefa no PostgreSQL. O orquestrador aguarda com timeout.
"""
import asyncio
import json

import aio_pika
import redis.asyncio as aioredis

from orchestrator.config import config
from orchestrator import db
from shared.contracts.message import MessageEnvelope
from shared.logging import get_logger

logger = get_logger("orchestrator.dispatch")

COMMANDS_EXCHANGE = "factory.commands"

_redis: aioredis.Redis | None = None
_rabbit_connection: aio_pika.RobustConnection | None = None
_rabbit_channel = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(config.redis_url, decode_responses=True)
    return _redis


async def get_channel():
    global _rabbit_connection, _rabbit_channel
    if _rabbit_channel is None or _rabbit_channel.is_closed:
        _rabbit_connection = await aio_pika.connect_robust(config.rabbitmq_url)
        _rabbit_channel = await _rabbit_connection.channel()
    return _rabbit_channel


async def dispatch_agent(
    *,
    workflow_run_id: str,
    correlation_id: str,
    agent_definition: dict,
    queue: str,
    stage: str,
    context: dict,
    priority: int = 5,
) -> dict:
    """Cria a tarefa, publica o comando e aguarda o AgentResult."""
    agent_id = agent_definition["id"]
    task_id = await db.create_task(
        workflow_run_id=workflow_run_id,
        type_=stage,
        title=f"{stage}: {agent_definition['name']}",
        agent_id=agent_id,
        priority=priority,
    )
    await db.record_audit_event(
        event_type="task.created",
        entity_type="task",
        entity_id=task_id,
        correlation_id=correlation_id,
        metadata_={"agent_id": agent_id, "stage": stage},
    )

    envelope = MessageEnvelope(
        correlation_id=correlation_id,
        workflow_run_id=workflow_run_id,
        task_id=task_id,
        agent_id=agent_id,
        command="execute_agent",
        priority=priority,
        payload={"stage": stage, "context": context},
    )
    channel = await get_channel()
    exchange = await channel.get_exchange(COMMANDS_EXCHANGE)
    await exchange.publish(
        aio_pika.Message(
            body=envelope.model_dump_json().encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=envelope.message_id,
            correlation_id=correlation_id,
        ),
        routing_key=queue,
    )
    await db.record_audit_event(
        event_type="task.queued",
        entity_type="task",
        entity_id=task_id,
        correlation_id=correlation_id,
        metadata_={"queue": queue},
    )

    # Aguarda resultado (worker grava em Redis e atualiza status no banco)
    redis_client = await get_redis()
    deadline = asyncio.get_event_loop().time() + config.stage_timeout_seconds
    while asyncio.get_event_loop().time() < deadline:
        raw = await redis_client.get(f"task_result:{task_id}")
        if raw:
            result = json.loads(raw)
            result["task_id"] = task_id
            return result
        status = await db.get_task_status(task_id)
        if status in ("FAILED", "CANCELLED"):
            return {
                "task_id": task_id,
                "agent_id": agent_id,
                "status": "failed",
                "summary": f"Tarefa terminou em {status} sem resultado",
                "findings": [],
                "artifacts": [],
            }
        await asyncio.sleep(config.poll_interval_seconds)

    logger.warning("stage_timeout", extra={"task_id": task_id, "agent_id": agent_id})
    return {
        "task_id": task_id,
        "agent_id": agent_id,
        "status": "failed",
        "summary": "Timeout aguardando o worker",
        "findings": [],
        "artifacts": [],
    }
