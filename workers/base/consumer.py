"""Consumidor base dos workers de domínio.

Regras de mensageria (seção 13.5):
- confirmação manual somente após persistência do resultado;
- retry com backoff exponencial;
- dead-letter após limite de tentativas;
- idempotência baseada em message_id (Redis SETNX);
- payloads grandes referenciados no MinIO.
"""
import asyncio
import json
import os

import aio_pika
import redis.asyncio as aioredis

from agents.registry import AgentRegistry
from agents.runtime.executor import AgentExecutor
from shared.contracts.message import MessageEnvelope
from shared.logging import configure_logging, get_logger
from workers.base import persistence
from workers.base.artifacts import store_result_artifact

logger = get_logger("workers.consumer")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://factory:factory@rabbitmq:5672/")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
MAX_ATTEMPTS = int(os.getenv("MESSAGE_MAX_ATTEMPTS", "3"))
RESULT_TTL_SECONDS = 24 * 3600
IDEMPOTENCY_TTL_SECONDS = 7 * 24 * 3600


class DomainWorker:
    def __init__(self, domain: str) -> None:
        self.domain = domain
        self.queue_name = f"factory.{domain}"
        self.registry = AgentRegistry.load_default()
        self.executor = AgentExecutor()
        self.redis: aioredis.Redis | None = None

    async def start(self) -> None:
        configure_logging()
        self.redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        while True:
            try:
                await self._consume()
            except Exception:  # noqa: BLE001
                logger.exception("consumer_error")
                await asyncio.sleep(5)

    async def _consume(self) -> None:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        dlx = await channel.declare_exchange(
            "factory.dead-letter", aio_pika.ExchangeType.FANOUT, durable=True
        )
        dlq = await channel.declare_queue("factory.dead-letter", durable=True)
        await dlq.bind(dlx)
        commands = await channel.declare_exchange(
            "factory.commands", aio_pika.ExchangeType.DIRECT, durable=True
        )
        queue = await channel.declare_queue(
            self.queue_name,
            durable=True,
            arguments={"x-dead-letter-exchange": "factory.dead-letter"},
        )
        await queue.bind(commands, routing_key=self.queue_name)
        logger.info(f"worker_started domain={self.domain}")

        async with queue.iterator() as iterator:
            async for message in iterator:
                await self._handle(message)

    async def _handle(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        try:
            envelope = MessageEnvelope.model_validate_json(message.body)
        except Exception:  # noqa: BLE001
            logger.exception("invalid_envelope")
            await message.reject(requeue=False)  # dead-letter
            return

        # Idempotência por message_id
        assert self.redis is not None
        first_time = await self.redis.set(
            f"processed:{envelope.message_id}", "1", nx=True, ex=IDEMPOTENCY_TTL_SECONDS
        )
        if not first_time:
            logger.info(f"duplicate_message message_id={envelope.message_id}")
            await message.ack()
            return

        try:
            await self._execute(envelope)
            await message.ack()  # confirmação manual após persistência
        except Exception:  # noqa: BLE001
            logger.exception("message_processing_failed")
            await self.redis.delete(f"processed:{envelope.message_id}")
            if envelope.attempt >= MAX_ATTEMPTS:
                await message.reject(requeue=False)  # dead-letter
            else:
                await asyncio.sleep(min(2 ** envelope.attempt, 30))  # backoff exponencial
                await self._republish(envelope)
                await message.ack()

    async def _republish(self, envelope: MessageEnvelope) -> None:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            exchange = await channel.get_exchange("factory.commands")
            retry = envelope.model_copy(update={"attempt": envelope.attempt + 1})
            await exchange.publish(
                aio_pika.Message(
                    body=retry.model_dump_json().encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    message_id=retry.message_id,
                    correlation_id=retry.correlation_id,
                ),
                routing_key=self.queue_name,
            )

    async def _execute(self, envelope: MessageEnvelope) -> None:
        task_id = envelope.task_id or ""
        agent_id = envelope.agent_id or ""
        definition = self.registry.get(agent_id)
        await persistence.update_task_status(task_id, "IN_PROGRESS", increment_attempt=True)
        await persistence.record_audit_event(
            event_type="agent.execution.started",
            actor_id=agent_id,
            entity_type="task",
            entity_id=task_id,
            correlation_id=envelope.correlation_id,
        )

        if definition is None or not definition.get("enabled", True):
            result_payload = {
                "agent_id": agent_id,
                "execution_id": persistence.new_id(),
                "status": "failed",
                "summary": f"Agente {agent_id} não encontrado ou desabilitado",
                "findings": [],
                "artifacts": [],
            }
            meta = {"model": None, "token_usage": 0, "duration_ms": 0, "error_code": "agent_not_found"}
        else:
            context = (envelope.payload or {}).get("context", {})
            result, meta = await self.executor.execute(definition, context)
            result_payload = result.model_dump()

        output_reference = await store_result_artifact(
            workflow_run_id=envelope.workflow_run_id or "",
            task_id=task_id,
            agent_id=agent_id,
            payload=result_payload,
        )
        execution_id = await persistence.record_agent_execution(
            task_id=task_id,
            agent_id=agent_id,
            model=meta.get("model"),
            status="COMPLETED" if result_payload["status"] != "failed" else "FAILED",
            input_reference=envelope.payload_reference,
            output_reference=output_reference,
            token_usage=int(meta.get("token_usage", 0)),
            duration_ms=int(meta.get("duration_ms", 0)),
            error_code=meta.get("error_code"),
        )
        await persistence.record_findings(task_id, execution_id, result_payload.get("findings", []))

        final_status = {
            "approved": "DONE",
            "changes_requested": "DONE",
            "blocked": "BLOCKED",
            "failed": "FAILED",
        }[result_payload["status"]]
        await persistence.update_task_status(task_id, final_status)
        await persistence.record_audit_event(
            event_type=(
                "agent.execution.completed"
                if result_payload["status"] != "failed"
                else "agent.execution.failed"
            ),
            actor_id=agent_id,
            entity_type="task",
            entity_id=task_id,
            correlation_id=envelope.correlation_id,
            metadata_={"status": result_payload["status"], "duration_ms": meta.get("duration_ms")},
        )

        assert self.redis is not None
        await self.redis.set(
            f"task_result:{task_id}", json.dumps(result_payload, default=str),
            ex=RESULT_TTL_SECONDS,
        )
        logger.info(
            "agent_execution_completed",
            extra={
                "correlation_id": envelope.correlation_id,
                "task_id": task_id,
                "agent_id": agent_id,
                "duration_ms": meta.get("duration_ms"),
            },
        )


def run(domain: str) -> None:
    asyncio.run(DomainWorker(domain).start())
