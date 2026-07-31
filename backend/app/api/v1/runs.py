from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.messaging.rabbitmq import publisher
from app.models import AuditEvent, Demand, Task, User, WorkflowRun
from app.observability.metrics import WORKFLOWS_STARTED
from app.schemas.api import RunOut, TaskOut, TimelineEntry
from app.services.audit import record_audit
from shared.contracts.states import (
    RUN_TRANSITIONS,
    InvalidTransitionError,
    RunStatus,
    validate_transition,
)

router = APIRouter(tags=["runs"])


@router.post("/demands/{demand_id}/runs", response_model=RunOut, status_code=201)
async def start_run(
    demand_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("DEVELOPER")),
) -> WorkflowRun:
    demand = await db.get(Demand, demand_id)
    if demand is None:
        raise HTTPException(404, "Demanda não encontrada")
    run = WorkflowRun(project_id=demand.project_id, demand_id=demand.id, status="CREATED")
    db.add(run)
    await db.flush()
    run.status = "QUEUED"
    await record_audit(
        db, event_type="workflow.started", actor_type="human", actor_id=user.username,
        entity_type="workflow_run", entity_id=run.id, correlation_id=run.correlation_id,
    )
    await db.commit()
    await db.refresh(run)
    WORKFLOWS_STARTED.inc()
    try:
        await publisher.publish_event(
            "workflow.run.requested",
            {
                "workflow_run_id": run.id,
                "demand_id": demand.id,
                "project_id": demand.project_id,
                "correlation_id": run.correlation_id,
            },
        )
    except Exception:  # noqa: BLE001 - orquestrador também faz polling do banco
        pass
    return run


@router.get("/runs/{run_id}", response_model=RunOut)
async def get_run(
    run_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> WorkflowRun:
    run = await db.get(WorkflowRun, run_id)
    if run is None:
        raise HTTPException(404, "Execução não encontrada")
    return run


@router.post("/runs/{run_id}/cancel", response_model=RunOut)
async def cancel_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("FACTORY_MANAGER")),
) -> WorkflowRun:
    run = await db.get(WorkflowRun, run_id)
    if run is None:
        raise HTTPException(404, "Execução não encontrada")
    try:
        validate_transition(RunStatus(run.status), RunStatus.CANCELLED, RUN_TRANSITIONS)
    except InvalidTransitionError as exc:
        raise HTTPException(409, str(exc)) from exc
    before = run.status
    run.status = "CANCELLED"
    run.finished_at = datetime.now(timezone.utc)
    await record_audit(
        db, event_type="workflow.cancelled", actor_type="human", actor_id=user.username,
        entity_type="workflow_run", entity_id=run.id, correlation_id=run.correlation_id,
        before_state={"status": before}, after_state={"status": "CANCELLED"},
    )
    await db.commit()
    await db.refresh(run)
    return run


@router.post("/runs/{run_id}/retry", response_model=RunOut)
async def retry_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("DEVELOPER")),
) -> WorkflowRun:
    run = await db.get(WorkflowRun, run_id)
    if run is None:
        raise HTTPException(404, "Execução não encontrada")
    if run.status not in ("FAILED_RETRYABLE",):
        raise HTTPException(409, f"Estado {run.status} não permite retry")
    run.status = "RETRYING"
    await record_audit(
        db, event_type="workflow.retried", actor_type="human", actor_id=user.username,
        entity_type="workflow_run", entity_id=run.id, correlation_id=run.correlation_id,
    )
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/runs/{run_id}/timeline", response_model=list[TimelineEntry])
async def run_timeline(
    run_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[TimelineEntry]:
    run = await db.get(WorkflowRun, run_id)
    if run is None:
        raise HTTPException(404, "Execução não encontrada")
    events = (
        await db.execute(
            select(AuditEvent)
            .where(AuditEvent.correlation_id == run.correlation_id)
            .order_by(AuditEvent.created_at)
        )
    ).scalars()
    return [
        TimelineEntry(
            timestamp=e.created_at,
            event_type=e.event_type,
            actor_type=e.actor_type,
            actor_id=e.actor_id,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            metadata=e.event_metadata,
        )
        for e in events
    ]


@router.get("/runs/{run_id}/tasks", response_model=list[TaskOut])
async def run_tasks(
    run_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Task]:
    result = await db.execute(
        select(Task).where(Task.workflow_run_id == run_id).order_by(Task.created_at)
    )
    return list(result.scalars())
