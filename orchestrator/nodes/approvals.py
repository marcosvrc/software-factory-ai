"""Nós de aprovação humana (seção 17): o grafo pausa até decisão via API."""
import asyncio

from orchestrator import db
from orchestrator.config import config
from orchestrator.state.state import DeliveryState, all_findings
from shared.logging import get_logger

logger = get_logger("orchestrator.approvals")

APPROVAL_POLL_SECONDS = 5.0

# Todos os gates com limite de ciclos automáticos (seção 9.1). Quando uma
# revisão humana é aprovada, os contadores são zerados: sem isso, o contador
# do gate que causou a escalada fica travado em MAX_CYCLES para sempre, e
# qualquer rejeição futura — mesmo a primeira nova tentativa — escala direto
# para human_review de novo, em vez de conceder um novo ciclo de tentativas.
ALL_GATES = [
    "intake",
    "scope",
    "architecture",
    "code_review",
    "tests",
    "qa",
    "security",
    "operational",
    "release",
]


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
        risks=[f for f in all_findings(state) if f.get("severity") in ("high", "critical")][:10],
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


async def intake_clarification(state: DeliveryState) -> dict:
    """Gate de esclarecimento de intake (seção 9, etapa intake_analysis).

    Disparado quando product.intake-analyst identifica lacunas na demanda
    (canal, escopo, volume, comportamentos essenciais, restrições não-
    funcionais, dados sensíveis, integrações, critérios de sucesso). Diferente
    dos outros gates (code_review, architecture, etc.), o agente NÃO pode
    resolver a lacuna por conta própria — só o solicitante sabe, por exemplo,
    se o canal deve ser web ou mobile. Por isso, toda vez que faltar
    informação, o fluxo pausa e pede a resposta via campo de justificativa da
    aprovação; a resposta é incorporada a clarification_notes e a análise é
    refeita. Após MAX_CYCLES rodadas sem completude, escala para human_review
    completo (decidir se segue mesmo incompleto ou cancela) — ver
    route_intake_analysis em orchestrator/graphs/software_delivery.py.
    """
    findings = state.get("stage_results", {}).get("intake_analysis", {}).get("results", [])
    gaps = [
        f.get("description", "")
        for r in findings
        for f in r.get("findings", [])
        if f.get("category") == "informacao_ausente"
    ]
    summary_gaps = "; ".join(gaps[:10]) or "Ver findings da etapa para o detalhamento completo."
    approval_id = await db.create_approval(
        workflow_run_id=state["workflow_run_id"],
        approval_type="intake_clarification",
        summary=(
            f"Informações insuficientes na demanda '{state.get('demand_title', '')}': "
            f"{summary_gaps}"
        ),
        recommendation=(
            "Responda no campo de justificativa às lacunas apontadas (ex.: canal de acesso, "
            "escopo desejado, volume esperado de usuários, regras de negócio essenciais, "
            "restrições não-funcionais, dados sensíveis, integrações, critério de sucesso). "
            "A resposta será usada para completar a análise."
        ),
    )
    await db.update_run(state["workflow_run_id"], status="WAITING_HUMAN")
    await db.record_audit_event(
        event_type="approval.requested",
        entity_type="approval",
        entity_id=approval_id,
        correlation_id=state["correlation_id"],
        metadata_={"approval_type": "intake_clarification"},
    )
    status = await _wait_for_approval(approval_id)
    await db.update_run(state["workflow_run_id"], status="RUNNING")
    rationale = await db.get_approval_rationale(approval_id) or ""
    await db.record_decision(
        workflow_run_id=state["workflow_run_id"],
        decision_type="intake_clarification",
        rationale=rationale or f"Decisão humana: {status}",
        selected_option=status,
        decided_by="human",
    )
    update: dict = {"cycles": {"intake": state.get("cycles", {}).get("intake", 0) + 1}}
    if status == "REJECTED":
        update["human_review_required"] = True
    elif rationale:
        update["clarification_notes"] = [rationale]
    return update


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
    update: dict = {"human_review_required": status != "APPROVED"}
    if status == "APPROVED":
        # Zera todos os contadores de ciclo: caso contrário o gate que causou
        # a escalada permanece travado em MAX_CYCLES para sempre, e qualquer
        # rejeição futura cairia direto em human_review de novo.
        update["cycles"] = {gate: 0 for gate in ALL_GATES}
    return update
