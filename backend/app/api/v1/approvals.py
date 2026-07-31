from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_role
from app.db.session import get_db
from app.messaging.rabbitmq import publisher
from app.models import Approval, User
from app.schemas.api import ApprovalDecision, ApprovalOut
from app.services.audit import record_audit

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut])
async def list_approvals(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Approval]:
    query = select(Approval).order_by(Approval.requested_at.desc())
    if status:
        query = query.where(Approval.status == status)
    return list((await db.execute(query)).scalars())


@router.get("/{approval_id}", response_model=ApprovalOut)
async def get_approval(
    approval_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> Approval:
    approval = await db.get(Approval, approval_id)
    if approval is None:
        raise HTTPException(404, "Aprovação não encontrada")
    return approval


async def _decide(
    approval_id: str, decision: str, body: ApprovalDecision, db: AsyncSession, user: User
) -> Approval:
    approval = await db.get(Approval, approval_id)
    if approval is None:
        raise HTTPException(404, "Aprovação não encontrada")
    if approval.status != "REQUESTED":
        raise HTTPException(409, f"Aprovação já decidida: {approval.status}")
    approval.status = decision
    approval.decided_by = user.username
    approval.rationale = body.rationale
    approval.decided_at = datetime.now(timezone.utc)
    await record_audit(
        db,
        event_type=f"approval.{decision.lower()}",
        actor_type="human",
        actor_id=user.username,
        entity_type="approval",
        entity_id=approval.id,
        after_state={"status": decision, "rationale": body.rationale},
    )
    await db.commit()
    await db.refresh(approval)
    try:
        await publisher.publish_event(
            f"approval.{decision.lower()}",
            {
                "approval_id": approval.id,
                "workflow_run_id": approval.workflow_run_id,
                "approval_type": approval.approval_type,
                "decided_by": user.username,
            },
        )
    except Exception:  # noqa: BLE001 - orquestrador também faz polling do banco
        pass
    return approval


@router.post("/{approval_id}/approve", response_model=ApprovalOut)
async def approve(
    approval_id: str,
    body: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("APPROVER")),
) -> Approval:
    return await _decide(approval_id, "APPROVED", body, db, user)


@router.post("/{approval_id}/reject", response_model=ApprovalOut)
async def reject(
    approval_id: str,
    body: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("APPROVER")),
) -> Approval:
    return await _decide(approval_id, "REJECTED", body, db, user)
