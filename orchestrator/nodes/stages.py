"""Nós do grafo de entrega (fluxo da seção 9).

Cada nó de etapa: monta contexto (14.2), seleciona agentes (23.3), despacha em
paralelo quando permitido (9.2), agrega resultados e registra auditoria.
"""
import asyncio
import json

from agents.registry import AgentRegistry
from orchestrator import db
from orchestrator.context_builder import build_context
from orchestrator.nodes.dispatch import dispatch_agent
from orchestrator.routing.router import CapabilityRouter
from orchestrator.state.state import DeliveryState
from shared.contracts.agent_result import AgentResult
from shared.logging import get_logger

logger = get_logger("orchestrator.stages")

_registry = AgentRegistry.load_default()
_router = CapabilityRouter(_registry)

RESPONSE_SCHEMA = AgentResult.model_json_schema()


async def _run_stage(state: DeliveryState, stage: str, parallel: bool = True) -> dict:
    definitions = _router.agents_for_stage(stage)
    if not definitions:
        return {
            "current_stage": stage,
            "stage_results": {stage: {"status": "approved", "summary": "sem agentes configurados"}},
        }

    context = build_context(
        objective=f"Etapa {stage} da demanda: {state.get('demand_title', '')}",
        required_inputs={
            "demand_title": state.get("demand_title", ""),
            "demand_description": state.get("demand_description", ""),
            "previous_results": json.dumps(state.get("stage_results", {}), default=str)[:4000],
        },
        relevant_artifacts=state.get("artifacts", []),
        applicable_decisions=state.get("decisions", []),
        pending_findings=[f for f in state.get("findings", []) if f.get("status") != "resolved"],
        constraints=["execução local", "sem acesso à internet no sandbox"],
        allowed_tools=[],
        response_schema=RESPONSE_SCHEMA,
    )

    async def _one(definition: dict) -> dict:
        return await dispatch_agent(
            workflow_run_id=state["workflow_run_id"],
            correlation_id=state["correlation_id"],
            agent_definition=definition,
            queue=_router.queue_for(definition),
            stage=stage,
            context={**context, "allowed_tools": definition.get("tools", {}).get("allowed", [])},
        )

    if parallel:
        results = list(await asyncio.gather(*[_one(d) for d in definitions]))
    else:
        results = [await _one(d) for d in definitions]

    findings = [f for r in results for f in r.get("findings", [])]
    artifacts = [a for r in results for a in r.get("artifacts", [])]
    blocked = any(r.get("status") == "blocked" for r in results)
    failed = any(r.get("status") == "failed" for r in results)
    changes = any(r.get("status") == "changes_requested" for r in results)
    critical = any(f.get("severity") == "critical" for f in findings)

    if blocked or failed:
        status = "failed"
    elif changes or critical:
        status = "changes_requested"
    else:
        status = "approved"

    summary = "; ".join(r.get("summary", "")[:200] for r in results)
    await db.update_run(state["workflow_run_id"], current_node=stage)
    await db.record_audit_event(
        event_type="state.changed",
        entity_type="workflow_run",
        entity_id=state["workflow_run_id"],
        correlation_id=state["correlation_id"],
        metadata_={"stage": stage, "status": status},
    )
    return {
        "current_stage": stage,
        "stage_results": {stage: {"status": status, "summary": summary, "results": results}},
        "findings": findings,
        "artifacts": artifacts,
    }


# --- nós concretos (assinaturas exigidas pelo LangGraph) ---
async def triage(state: DeliveryState) -> dict:
    result = await _run_stage(state, "triage")
    await db.update_run(state["workflow_run_id"], status="RUNNING")
    return result


async def product_discovery(state: DeliveryState) -> dict:
    return await _run_stage(state, "product_discovery")


async def requirements(state: DeliveryState) -> dict:
    return await _run_stage(state, "requirements")


async def architecture(state: DeliveryState) -> dict:
    return await _run_stage(state, "architecture")


async def technical_planning(state: DeliveryState) -> dict:
    return await _run_stage(state, "technical_planning")


async def development(state: DeliveryState) -> dict:
    return await _run_stage(state, "development", parallel=False)


async def code_review(state: DeliveryState) -> dict:
    return await _run_stage(state, "code_review")


async def automated_tests(state: DeliveryState) -> dict:
    return await _run_stage(state, "automated_tests")


async def functional_qa(state: DeliveryState) -> dict:
    return await _run_stage(state, "functional_qa")


async def security_compliance(state: DeliveryState) -> dict:
    return await _run_stage(state, "security_compliance")


async def operational_validation(state: DeliveryState) -> dict:
    return await _run_stage(state, "operational_validation")


async def documentation_release(state: DeliveryState) -> dict:
    return await _run_stage(state, "documentation_release")
