"""Publicador de comandos e eventos com envelope da seção 13.4."""
import json

import aio_pika

from app.core.config import get_settings
from app.messaging.topology import COMMANDS_EXCHANGE, EVENTS_EXCHANGE, declare_topology
from shared.contracts.message import MessageEnvelope


class RabbitPublisher:
    def __init__(self) -> None:
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None

    async def connect(self) -> None:
        settings = get_settings()
        self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self._channel = await self._connection.channel()
        await declare_topology(self._channel)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()

    async def publish_command(self, queue: str, envelope: MessageEnvelope) -> None:
        assert self._channel is not None, "Publisher não conectado"
        exchange = await self._channel.get_exchange(COMMANDS_EXCHANGE)
        message = aio_pika.Message(
            body=envelope.model_dump_json().encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=envelope.message_id,
            correlation_id=envelope.correlation_id,
            priority=envelope.priority,
        )
        await exchange.publish(message, routing_key=queue)

    async def publish_event(self, event_type: str, payload: dict) -> None:
        assert self._channel is not None, "Publisher não conectado"
        exchange = await self._channel.get_exchange(EVENTS_EXCHANGE)
        message = aio_pika.Message(
            body=json.dumps(payload, default=str).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key=event_type)


publisher = RabbitPublisher()
