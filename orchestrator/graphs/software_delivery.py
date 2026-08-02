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


def _cycles_exceeded(state: DeliveryState, gate: str) -> bool:
    """Verifica o contador ATUAL (já persistido) do gate, sem incrementar."""
    return state.get("cycles", {}).get(gate, 0) >= MAX_CYCLES


def _intake_complete(state: DeliveryState) -> bool:
    status = _stage_status(state, "intake_analysis")
    return status == "approved"


# ---- roteadores condicionais ----
# Importante: roteadores do LangGraph apenas decidem a próxima aresta e não
# podem persistir alterações de estado. O incremento do contador de ciclos é
# feito pelos nós "*_cycle" (ver _cycle_node), inseridos no caminho de retorno
# de cada gate. Os roteadores só leem o valor já persistido.
def route_intake_analysis(state: DeliveryState) -> str:
    """Gate de completude de intake (seção 9): diferente dos demais gates, a
    lacuna não pode ser resolvida pelo próprio agente — só o solicitante sabe
    responder, por exemplo, se o canal é web ou mobile. Por isso, toda
    reprovação vai direto para intake_clarification (pede resposta ao
    solicitante), não para um retry automático silencioso."""
    if _intake_complete(state):
        return "product_discovery"
    if _cycles_exceeded(state, "intake"):
        return "intake_escalate"
    return "intake_clarification"


def route_scope(state: DeliveryState) -> str:
    if state.get("scope_approved"):
        return "architecture"
    if _cycles_exceeded(state, "scope"):
        return "scope_escalate"
    return "scope_cycle"  # Reprovado -> incrementa ciclo e retorna a produto/descoberta


def route_architecture_gate(state: DeliveryState) -> str:
    status = _stage_status(state, "architecture")
    if status == "approved":
        return "technical_planning"
    if _cycles_exceeded(state, "architecture"):
        return "architecture_escalate"
    return "architecture_cycle"  # Ajustes


def route_code_review(state: DeliveryState) -> str:
    status = _stage_status(state, "code_review")
    if status == "approved":
        return "automated_tests"
    if _cycles_exceeded(state, "code_review"):
        return "code_review_escalate"
    return "code_review_cycle"


def route_tests(state: DeliveryState) -> str:
    status = _stage_status(state, "automated_tests")
    if status == "approved":
        return "functional_qa"
    if _cycles_exceeded(state, "tests"):
        return "tests_escalate"
    return "tests_cycle"


def route_qa(state: DeliveryState) -> str:
    status = _stage_status(state, "functional_qa")
    if status == "approved":
        return "security_compliance"
    if _cycles_exceeded(state, "qa"):
        return "qa_escalate"
    return "qa_cycle"


def route_security(state: DeliveryState) -> str:
    status = _stage_status(state, "security_compliance")
    if status == "approved":
        return "operational_validation"
    if _cycles_exceeded(state, "security"):
        return "security_escalate"
    return "security_cycle"


def route_operational(state: DeliveryState) -> str:
    status = _stage_status(state, "operational_validation")
    if status == "approved":
        return "documentation_release"
    if _cycles_exceeded(state, "operational"):
        return "operational_escalate"
    return "operational_cycle"  # Reprovado -> incrementa ciclo e volta ao planejamento


def route_release(state: DeliveryState) -> str:
    if state.get("release_approved"):
        return "delivered"
    if _cycles_exceeded(state, "release"):
        return "release_escalate"
    return "release_cycle"


# Nó de destino a retomar quando a revisão humana aprova a continuidade,
# indexado pelo gate que causou a escalada (ver *_escalate abaixo). Cada
# destino corresponde à etapa que sucederia o gate em caso de aprovação
# automática, evitando pular etapas (ex.: "scope" -> "architecture", nunca
# direto para "technical_planning") ou refazer o pipeline do zero sem motivo.
RESUME_AFTER_GATE = {
    "intake": "product_discovery",
    "scope": "architecture",
    "architecture": "technical_planning",
    "code_review": "automated_tests",
    "tests": "functional_qa",
    "qa": "security_compliance",
    "security": "operational_validation",
    "operational": "documentation_release",
    "release": "delivered",
}


def route_human_review(state: DeliveryState) -> str:
    if state.get("human_review_required"):
        return "cancelled"
    gate = state.get("escalated_gate")
    return RESUME_AFTER_GATE.get(gate, "technical_planning")


# ---- contadores de ciclo (nós de incremento antes de voltar) ----
def _cycle_node(gate: str):
    async def _inc(state: DeliveryState) -> dict:
        return {"cycles": {gate: _bump(state, gate)}}

    return _inc


# ---- marcação do gate escalado (nós antes de entrar em human_review) ----
def _escalate_node(gate: str):
    async def _mark(state: DeliveryState) -> dict:
        return {"escalated_gate": gate}

    return _mark


async def delivered(state: DeliveryState) -> dict:
    return {"current_stage": "delivered"}


async def cancelled(state: DeliveryState) -> dict:
    return {"current_stage": "cancelled", "failure_reason": "revisão humana negou continuidade"}


def build_graph(checkpointer=None):
    graph = StateGraph(DeliveryState)

    graph.add_node("triage", stages.triage)
    graph.add_node("intake_analysis", stages.intake_analysis)
    graph.add_node("intake_clarification", approvals.intake_clarification)
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

    # Nós de incremento de ciclo: persistem o contador antes de retornar à
    # etapa anterior, garantindo que o limite de MAX_CYCLES seja alcançável.
    graph.add_node("intake_escalate", _escalate_node("intake"))
    graph.add_node("scope_cycle", _cycle_node("scope"))
    graph.add_node("architecture_cycle", _cycle_node("architecture"))
    graph.add_node("code_review_cycle", _cycle_node("code_review"))
    graph.add_node("tests_cycle", _cycle_node("tests"))
    graph.add_node("qa_cycle", _cycle_node("qa"))
    graph.add_node("security_cycle", _cycle_node("security"))
    graph.add_node("operational_cycle", _cycle_node("operational"))
    graph.add_node("release_cycle", _cycle_node("release"))

    # Nós de escalada: marcam qual gate esgotou os ciclos antes de entrar em
    # human_review, para que route_human_review saiba onde retomar a
    # execução em caso de aprovação (ver RESUME_AFTER_GATE).
    graph.add_node("scope_escalate", _escalate_node("scope"))
    graph.add_node("architecture_escalate", _escalate_node("architecture"))
    graph.add_node("code_review_escalate", _escalate_node("code_review"))
    graph.add_node("tests_escalate", _escalate_node("tests"))
    graph.add_node("qa_escalate", _escalate_node("qa"))
    graph.add_node("security_escalate", _escalate_node("security"))
    graph.add_node("operational_escalate", _escalate_node("operational"))
    graph.add_node("release_escalate", _escalate_node("release"))

    graph.set_entry_point("triage")
    graph.add_edge("triage", "intake_analysis")
    graph.add_conditional_edges(
        "intake_analysis",
        route_intake_analysis,
        {
            "product_discovery": "product_discovery",
            "intake_clarification": "intake_clarification",
            "intake_escalate": "intake_escalate",
        },
    )
    graph.add_edge("intake_clarification", "intake_analysis")
    graph.add_edge("intake_escalate", "human_review")
    graph.add_edge("product_discovery", "requirements")
    graph.add_edge("requirements", "scope_approval")
    graph.add_conditional_edges(
        "scope_approval",
        route_scope,
        {
            "architecture": "architecture",
            "scope_cycle": "scope_cycle",
            "scope_escalate": "scope_escalate",
        },
    )
    graph.add_edge("scope_cycle", "product_discovery")
    graph.add_edge("scope_escalate", "human_review")
    graph.add_conditional_edges(
        "architecture",
        route_architecture_gate,
        {
            "technical_planning": "technical_planning",
            "architecture_cycle": "architecture_cycle",
            "architecture_escalate": "architecture_escalate",
        },
    )
    graph.add_edge("architecture_cycle", "architecture")
    graph.add_edge("architecture_escalate", "human_review")
    graph.add_edge("technical_planning", "development")
    graph.add_edge("development", "code_review")
    graph.add_conditional_edges(
        "code_review",
        route_code_review,
        {
            "automated_tests": "automated_tests",
            "code_review_cycle": "code_review_cycle",
            "code_review_escalate": "code_review_escalate",
        },
    )
    graph.add_edge("code_review_cycle", "development")
    graph.add_edge("code_review_escalate", "human_review")
    graph.add_conditional_edges(
        "automated_tests",
        route_tests,
        {
            "functional_qa": "functional_qa",
            "tests_cycle": "tests_cycle",
            "tests_escalate": "tests_escalate",
        },
    )
    graph.add_edge("tests_cycle", "development")
    graph.add_edge("tests_escalate", "human_review")
    graph.add_conditional_edges(
        "functional_qa",
        route_qa,
        {
            "security_compliance": "security_compliance",
            "qa_cycle": "qa_cycle",
            "qa_escalate": "qa_escalate",
        },
    )
    graph.add_edge("qa_cycle", "development")
    graph.add_edge("qa_escalate", "human_review")
    graph.add_conditional_edges(
        "security_compliance",
        route_security,
        {
            "operational_validation": "operational_validation",
            "security_cycle": "security_cycle",
            "security_escalate": "security_escalate",
        },
    )
    graph.add_edge("security_cycle", "development")
    graph.add_edge("security_escalate", "human_review")
    graph.add_conditional_edges(
        "operational_validation",
        route_operational,
        {
            "documentation_release": "documentation_release",
            "operational_cycle": "operational_cycle",
            "operational_escalate": "operational_escalate",
        },
    )
    graph.add_edge("operational_cycle", "technical_planning")
    graph.add_edge("operational_escalate", "human_review")
    graph.add_edge("documentation_release", "release_approval")
    graph.add_conditional_edges(
        "release_approval",
        route_release,
        {
            "delivered": "delivered",
            "release_cycle": "release_cycle",
            "release_escalate": "release_escalate",
        },
    )
    graph.add_edge("release_cycle", "technical_planning")
    graph.add_edge("release_escalate", "human_review")
    graph.add_conditional_edges(
        "human_review",
        route_human_review,
        {
            "cancelled": "cancelled",
            "product_discovery": "product_discovery",
            "architecture": "architecture",
            "technical_planning": "technical_planning",
            "automated_tests": "automated_tests",
            "functional_qa": "functional_qa",
            "security_compliance": "security_compliance",
            "operational_validation": "operational_validation",
            "documentation_release": "documentation_release",
            "delivered": "delivered",
        },
    )
    graph.add_edge("delivered", END)
    graph.add_edge("cancelled", END)

    return graph.compile(checkpointer=checkpointer)
