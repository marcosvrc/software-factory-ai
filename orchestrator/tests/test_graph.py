"""Testes do grafo (seção 26.4): roteadores condicionais e limite de ciclos."""
from orchestrator.graphs.software_delivery import (
    MAX_CYCLES,
    RESUME_AFTER_GATE,
    _cycle_node,
    _escalate_node,
    build_graph,
    route_architecture_gate,
    route_code_review,
    route_human_review,
    route_intake_analysis,
    route_scope,
)
from orchestrator.nodes.approvals import ALL_GATES, human_review_required


def _state(**kw):
    base = {"stage_results": {}, "cycles": {}}
    base.update(kw)
    return base


def test_scope_approved_goes_to_architecture():
    assert route_scope(_state(scope_approved=True)) == "architecture"


def test_scope_rejected_increments_cycle_before_returning_to_discovery():
    # O roteador aponta para o nó "scope_cycle", que persiste o contador de
    # ciclos antes de seguir para "product_discovery" (ver software_delivery.py).
    assert route_scope(_state(scope_approved=False)) == "scope_cycle"


def test_scope_exceeds_cycles_goes_to_escalate_node():
    state = _state(scope_approved=False, cycles={"scope": MAX_CYCLES})
    assert route_scope(state) == "scope_escalate"


def test_code_review_changes_requested_loops_to_development():
    state = _state(stage_results={"code_review": {"status": "changes_requested"}})
    assert route_code_review(state) == "code_review_cycle"


def test_code_review_approved_moves_to_tests():
    state = _state(stage_results={"code_review": {"status": "approved"}})
    assert route_code_review(state) == "automated_tests"


def test_architecture_gate_limits_cycles():
    state = _state(
        stage_results={"architecture": {"status": "changes_requested"}},
        cycles={"architecture": MAX_CYCLES},
    )
    assert route_architecture_gate(state) == "architecture_escalate"


async def test_cycle_node_persists_increment():
    """Regressão: o incremento de ciclo precisa ser persistido no estado,
    caso contrário o grafo nunca atinge MAX_CYCLES e entra em recursão
    infinita (GraphRecursionError)."""
    node = _cycle_node("code_review")
    state = _state(cycles={"code_review": 1})
    update = await node(state)
    assert update == {"cycles": {"code_review": 2}}


async def test_repeated_rejections_eventually_exceed_cycle_limit():
    """Simula o merge de estado do LangGraph (reducer _merge_dict) para
    garantir que, após MAX_CYCLES rejeições consecutivas, o roteador escala
    para o nó de escalada em vez de repetir indefinidamente."""
    node = _cycle_node("code_review")
    state = _state(stage_results={"code_review": {"status": "changes_requested"}})
    for _ in range(MAX_CYCLES):
        assert route_code_review(state) == "code_review_cycle"
        update = await node(state)
        state["cycles"] = {**state["cycles"], **update["cycles"]}
    assert route_code_review(state) == "code_review_escalate"


def test_build_graph_compiles_without_recursion_edges_missing():
    """Regressão: garante que todos os nós de ciclo estão registrados e
    conectados, evitando erro de nó órfão na compilação do grafo."""
    graph = build_graph()
    assert graph is not None


async def test_escalate_node_marks_gate_for_resume_routing():
    """O nó de escalada precisa persistir qual gate esgotou os ciclos, para
    que route_human_review saiba onde retomar após aprovação."""
    node = _escalate_node("code_review")
    update = await node(_state())
    assert update == {"escalated_gate": "code_review"}


def test_resume_after_gate_never_skips_a_stage():
    """Regressão: retomar sempre a etapa que sucede o gate escalado, nunca
    pulando etapas (ex.: 'scope' deve retomar em 'architecture', não direto
    em 'technical_planning', que pularia a etapa de arquitetura)."""
    assert RESUME_AFTER_GATE["scope"] == "architecture"
    assert RESUME_AFTER_GATE["architecture"] == "technical_planning"
    assert RESUME_AFTER_GATE["code_review"] == "automated_tests"


def test_route_human_review_resumes_at_stage_after_escalated_gate():
    state = _state(human_review_required=False, escalated_gate="code_review")
    assert route_human_review(state) == "automated_tests"


def test_route_human_review_cancels_when_required():
    state = _state(human_review_required=True, escalated_gate="code_review")
    assert route_human_review(state) == "cancelled"


async def test_human_review_approval_resets_all_gate_cycles(monkeypatch):
    """Regressão: sem resetar os contadores, o gate que causou a escalada
    fica travado em MAX_CYCLES para sempre. Depois disso, qualquer nova
    rejeição naquele gate — mesmo a primeira — escalaria direto para
    human_review de novo, em vez de conceder novas MAX_CYCLES tentativas."""

    async def fake_request_and_wait(state, approval_type, summary, recommendation):
        return "APPROVED"

    monkeypatch.setattr(
        "orchestrator.nodes.approvals._request_and_wait", fake_request_and_wait
    )
    state = _state(cycles={gate: MAX_CYCLES for gate in ALL_GATES})
    update = await human_review_required(state)
    assert update["human_review_required"] is False
    assert update["cycles"] == {gate: 0 for gate in ALL_GATES}


def test_intake_analysis_approved_moves_to_product_discovery():
    state = _state(stage_results={"intake_analysis": {"status": "approved"}})
    assert route_intake_analysis(state) == "product_discovery"


def test_intake_analysis_incomplete_goes_to_clarification():
    """Regressão principal: diferente dos demais gates, uma demanda com
    lacunas (canal, escopo, volume, etc.) não deve retornar automaticamente
    a uma etapa anterior — precisa pedir a informação ao solicitante, já que
    o próprio agente não pode inventar a resposta."""
    state = _state(stage_results={"intake_analysis": {"status": "changes_requested"}})
    assert route_intake_analysis(state) == "intake_clarification"


def test_intake_analysis_exceeds_cycles_goes_to_escalate():
    state = _state(
        stage_results={"intake_analysis": {"status": "changes_requested"}},
        cycles={"intake": MAX_CYCLES},
    )
    assert route_intake_analysis(state) == "intake_escalate"


def test_resume_after_intake_escalation_goes_to_product_discovery():
    assert RESUME_AFTER_GATE["intake"] == "product_discovery"


def test_intake_is_included_in_all_gates_reset():
    """Regressão: se 'intake' não estiver em ALL_GATES, o contador de ciclos
    do gate de intake ficaria travado no limite para sempre após a primeira
    escalada para human_review, mesmo com aprovação."""
    assert "intake" in ALL_GATES
