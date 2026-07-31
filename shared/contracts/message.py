"""Envelope de mensagem da mensageria (seção 13.4 da proposta).

Regras (seção 13.5):
- confirmação manual após persistência do resultado;
- retry com backoff exponencial;
- dead-letter após limite de tentativas;
- idempotência baseada em message_id;
- toda mensagem deve conter correlation_id;
- payloads grandes ficam no MinIO (payload_reference).
"""
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MessageEnvelope(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str
    causation_id: str | None = None
    workflow_run_id: str | None = None
    task_id: str | None = None
    agent_id: str | None = None
    command: str = "execute_agent"
    priority: int = 5
    attempt: int = 1
    created_at: datetime = Field(default_factory=_now)
    payload_reference: str | None = None
    payload: dict | None = None
