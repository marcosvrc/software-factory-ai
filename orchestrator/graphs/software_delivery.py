"""Grafo principal de entrega de software (fluxo completo da seção 9).

Demanda -> Triagem -> Produto -> Requisitos -> {Aprovação de escopo} ->
Arquitetura -> {Architecture gate} -> Planejamento -> Desenvolvimento ->
Code review -> Testes -> QA -> Segurança -> Validação operacional ->
Documentação/Release -> {Aprovação humana} -> Entrega.

Limites (9.1): máximo de 3 ciclos automáticos por gate; depois
HUMAN_REVIEW_REQUIRED. Loops sempre referenciam os findings que os motivaram.
"""
from langgraph.graph import END, StateGraph

from orchestrator.config import config
from orchestrator.nodes import approvals, stages
from orchestrator.state.state import DeliveryState

MAX_CYCLES = config.max_gate_cycles


def _bump(state: DeliveryState, gate: str) -> int:
    return state.get("cycles", {}).get(gate, 0) + 1


def _stage_status(state: DeliveryState, stage: str) -> str:
    return state.get("stage_results", {}).get(stage, {}).get("status", "approved")


# ---- roteadores condicionais ----
def route_scope(state: DeliveryState) -> str:
    if state.get("scope_approved"):
        return "architecture"
    if _bump(state, "scope") > MAX_CYCLES:
        return "human_review"
    return "product_discovery"  # Reprovado -> retorna a produto e descoberta


def route_architecture_gate(state: DeliveryState) -> str:
    status = _stage_status(state, "architecture")
    if status == "approved":
        return "technical_planning"
    if _bump(state, "architecture") > MAX_CYCLES:
        return "human_review"
    return "architecture"  # Ajustes


def route_code_review(state: DeliveryState) -> str:
    status = _stage_status(state, "code_review")
    if status == "approved":
        return "automated_tests"
    if _bump(state, "code_review") > MAX_CYCLES:
        return "human_review"
    return "development"


def route_tests(state: DeliveryState) -> str:
    status = _stage_status(state, "automated_tests")
    if status == "approved":
        return "functional_qa"
    if _bump(state, "tests") > MAX_CYCLES:
        return "human_review"
    return "development"


def route_qa(state: DeliveryState) -> str:
    status = _stage_status(state, "functional_qa")
    if status == "approved":
        return "security_compliance"
    if _bump(state, "qa") > MAX_CYCLES:
        return "human_review"
    return "development"


def route_security(state: DeliveryState) -> str:
    status = _stage_status(state, "security_compliance")
    if status == "approved":
        return "operational_validation"
    if _bump(state, "security") > MAX_CYCLES:
        return "human_review"
    return "development"


def route_operational(state: DeliveryState) -> str:
    status = _stage_status(state, "operational_validation")
    if status == "approved":
        return "documentation_release"
    if _bump(state, "operational") > MAX_CYCLES:
        return "human_review"
    return "technical_planning"  # Reprovado -> volta ao planejamento


def route_release(state: DeliveryState) -> str:
    if state.get("release_approved"):
        return "delivered"
    if _bump(state, "release") > MAX_CYCLES:
        return "human_review"
    return "technical_planning"


def route_human_review(state: DeliveryState) -> str:
    return "cancelled" if state.get("human_review_required") else "technical_planning"


# ---- contadores de ciclo (nós de incremento antes de voltar) ----
def _cycle_node(gate: str):
    async def _inc(state: DeliveryState) -> dict:
        return {"cycles": {gate: _bump(state, gate)}}

    return _inc


async def delivered(state: DeliveryState) -> dict:
    return {"current_stage": "delivered"}


async def cancelled(state: DeliveryState) -> dict:
    return {"current_stage": "cancelled", "failure_reason": "revisão humana negou continuidade"}


def build_graph(checkpointer=None):
    graph = StateGraph(DeliveryState)

    graph.add_node("triage", stages.triage)
    graph.add_node("product_discovery", stages.product_discovery)
    graph.add_node("requirements", stages.requirements)
    graph.add_node("scope_approval", approvals.scope_approval)
    graph.add_node("architecture", stages.architecture)
    graph.add_node("technical_planning", stages.technical_planning)
    graph.add_node("development", stages.development)
    graph.add_node("code_review", stages.code_review)
    graph.add_node("automated_tests", stages.automated_tests)
    graph.add_node("functional_qa", stages.functional_qa)
    graph.add_node("security_compliance", stages.security_compliance)
    graph.add_node("operational_validation", stages.operational_validation)
    graph.add_node("documentation_release", stages.documentation_release)
    graph.add_node("release_approval", approvals.release_approval)
    graph.add_node("human_review", approvals.human_review_required)
    graph.add_node("delivered", delivered)
    graph.add_node("cancelled", cancelled)

    graph.set_entry_point("triage")
    graph.add_edge("triage", "product_discovery")
    graph.add_edge("product_discovery", "requirements")
    graph.add_edge("requirements", "scope_approval")
    graph.add_conditional_edges(
        "scope_approval",
        route_scope,
        {
            "architecture": "architecture",
            "product_discovery": "product_discovery",
            "human_review": "human_review",
        },
    )
    graph.add_conditional_edges(
        "architecture",
        route_architecture_gate,
        {
            "technical_planning": "technical_planning",
            "architecture": "architecture",
            "human_review": "human_review",
        },
    )
    graph.add_edge("technical_planning", "development")
    graph.add_edge("development", "code_review")
    graph.add_conditional_edges(
        "code_review",
        route_code_review,
        {
            "automated_tests": "automated_tests",
            "development": "development",
            "human_review": "human_review",
        },
    )
    graph.add_conditional_edges(
        "automated_tests",
        route_tests,
        {
            "functional_qa": "functional_qa",
            "development": "development",
            "human_review": "human_review",
        },
    )
    graph.add_conditional_edges(
        "functional_qa",
        route_qa,
        {
            "security_compliance": "security_compliance",
            "development": "development",
            "human_review": "human_review",
        },
    )
    graph.add_conditional_edges(
        "security_compliance",
        route_security,
        {
            "operational_validation": "operational_validation",
            "development": "development",
            "human_review": "human_review",
        },
    )
    graph.add_conditional_edges(
        "operational_validation",
        route_operational,
        {
            "documentation_release": "documentation_release",
            "technical_planning": "technical_planning",
            "human_review": "human_review",
        },
    )
    graph.add_edge("documentation_release", "release_approval")
    graph.add_conditional_edges(
        "release_approval",
        route_release,
        {
            "delivered": "delivered",
            "technical_planning": "technical_planning",
            "human_review": "human_review",
        },
    )
    graph.add_conditional_edges(
        "human_review",
        route_human_review,
        {"cancelled": "cancelled", "technical_planning": "technical_planning"},
    )
    graph.add_edge("delivered", END)
    graph.add_edge("cancelled", END)

    return graph.compile(checkpointer=checkpointer)
