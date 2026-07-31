"""Registro de eventos de auditoria append-only (seção 20.5)."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent


async def record_audit(
    db: AsyncSession,
    *,
    event_type: str,
    actor_type: str,
    actor_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    correlation_id: str | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        correlation_id=correlation_id,
        before_state=before_state,
        after_state=after_state,
        event_metadata=metadata,
    )
    db.add(event)
    await db.flush()
    return event
