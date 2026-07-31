"""Nós de aprovação humana (seção 17): o grafo pausa até decisão via API."""
import asyncio

from orchestrator import db
from orchestrator.config import config
from orchestrator.state.state import DeliveryState
from shared.logging import get_logger

logger = get_logger("orchestrator.approvals")

APPROVAL_POLL_SECONDS = 5.0


async def _wait_for_approval(approval_id: str) -> str:
    """Aguarda decisão humana (REQUESTED -> APPROVED/REJECTED/EXPIRED/CANCELLED)."""
    while True:
        status = await db.get_approval_status(approval_id)
        if status and status != "REQUESTED":
            return status
        await asyncio.sleep(APPROVAL_POLL_SECONDS)


async def _request_and_wait(
    state: DeliveryState, approval_type: str, summary: str, recommendation: str
) -> str:
    await db.update_run(state["workflow_run_id"], status="WAITING_HUMAN")
    approval_id = await db.create_approval(
        workflow_run_id=state["workflow_run_id"],
        approval_type=approval_type,
        summary=summary,
        recommendation=recommendation,
        artifacts=state.get("artifacts", [])[:20],
        risks=[f for f in state.get("findings", []) if f.get("severity") in ("high", "critical")][
            :10
        ],
    )
    await db.record_audit_event(
        event_type="approval.requested",
        entity_type="approval",
        entity_id=approval_id,
        correlation_id=state["correlation_id"],
        metadata_={"approval_type": approval_type},
    )
    status = await _wait_for_approval(approval_id)
    await db.update_run(state["workflow_run_id"], status="RUNNING")
    await db.record_decision(
        workflow_run_id=state["workflow_run_id"],
        decision_type=approval_type,
        rationale=f"Decisão humana: {status}",
        selected_option=status,
        decided_by="human",
    )
    return status


async def scope_approval(state: DeliveryState) -> dict:
    """Gate de aprovação de escopo (obrigatória, seção 17.1)."""
    status = await _request_and_wait(
        state,
        "scope",
        f"Aprovação de escopo da demanda: {state.get('demand_title', '')}",
        "Aprovar se problema, objetivo, usuário, valor e métricas estão claros (Gate 1/2).",
    )
    return {"scope_approved": status == "APPROVED"}


async def release_approval(state: DeliveryState) -> dict:
    """Aprovação humana de release (Gate 9)."""
    status = await _request_and_wait(
        state,
        "release",
        f"Release da demanda: {state.get('demand_title', '')}",
        "Aprovar somente com todos os gates aprovados e release notes disponíveis.",
    )
    return {"release_approved": status == "APPROVED"}


async def human_review_required(state: DeliveryState) -> dict:
    """Após 3 ciclos automáticos, item vai para revisão humana (seção 9.1)."""
    status = await _request_and_wait(
        state,
        "human_review",
        f"Limite de ciclos automáticos atingido na etapa {state.get('current_stage', '')}",
        "Revisar os findings acumulados e decidir prosseguir ou cancelar.",
    )
    return {"human_review_required": status != "APPROVED"}
