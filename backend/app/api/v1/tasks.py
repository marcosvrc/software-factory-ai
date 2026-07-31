from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.models import Task, User
from app.schemas.api import TaskOut
from app.services.audit import record_audit

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> Task:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "Tarefa não encontrada")
    return task


@router.post("/{task_id}/retry", response_model=TaskOut)
async def retry_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("DEVELOPER")),
) -> Task:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "Tarefa não encontrada")
    if task.status not in ("FAILED", "BLOCKED"):
        raise HTTPException(409, f"Estado {task.status} não permite retry")
    if task.attempt >= task.max_attempts:
        raise HTTPException(409, "Limite de tentativas excedido; requer revisão humana")
    before = task.status
    task.status = "READY"
    await record_audit(
        db, event_type="task.retried", actor_type="human", actor_id=user.username,
        entity_type="task", entity_id=task.id,
        before_state={"status": before}, after_state={"status": "READY"},
    )
    await db.commit()
    await db.refresh(task)
    return task
