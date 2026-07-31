"""Topologia RabbitMQ (seções 13.2 e 13.3 da proposta)."""
import aio_pika
from aio_pika.abc import AbstractChannel

COMMANDS_EXCHANGE = "factory.commands"
EVENTS_EXCHANGE = "factory.events"
DEAD_LETTER_EXCHANGE = "factory.dead-letter"

DOMAIN_QUEUES = [
    "factory.product",
    "factory.architecture",
    "factory.engineering",
    "factory.validation",
    "factory.security",
    "factory.operations",
    "factory.delivery",
    "factory.governance",
]
DEAD_LETTER_QUEUE = "factory.dead-letter"


async def declare_topology(channel: AbstractChannel) -> None:
    commands = await channel.declare_exchange(
        COMMANDS_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True
    )
    await channel.declare_exchange(EVENTS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
    dlx = await channel.declare_exchange(
        DEAD_LETTER_EXCHANGE, aio_pika.ExchangeType.FANOUT, durable=True
    )

    dlq = await channel.declare_queue(DEAD_LETTER_QUEUE, durable=True)
    await dlq.bind(dlx)

    for queue_name in DOMAIN_QUEUES:
        queue = await channel.declare_queue(
            queue_name,
            durable=True,
            arguments={"x-dead-letter-exchange": DEAD_LETTER_EXCHANGE},
        )
        await queue.bind(commands, routing_key=queue_name)
