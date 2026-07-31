"""Configuração do orquestrador."""
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class OrchestratorConfig:
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql+asyncpg://factory:factory@postgres:5432/factory"
        )
    )
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://redis:6379/0"))
    rabbitmq_url: str = field(
        default_factory=lambda: os.getenv(
            "RABBITMQ_URL", "amqp://factory:factory@rabbitmq:5672/"
        )
    )
    max_gate_cycles: int = field(default_factory=lambda: int(os.getenv("MAX_GATE_CYCLES", "3")))
    stage_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("STAGE_TIMEOUT_SECONDS", "1800"))
    )
    poll_interval_seconds: float = field(
        default_factory=lambda: float(os.getenv("POLL_INTERVAL_SECONDS", "2.0"))
    )


config = OrchestratorConfig()
