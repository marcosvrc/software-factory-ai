"""Testes do grafo (seção 26.4): roteadores condicionais e limite de ciclos."""
from orchestrator.graphs.software_delivery import (
    MAX_CYCLES,
    route_architecture_gate,
    route_code_review,
    route_scope,
)


def _state(**kw):
    base = {"stage_results": {}, "cycles": {}}
    base.update(kw)
    return base


def test_scope_approved_goes_to_architecture():
    assert route_scope(_state(scope_approved=True)) == "architecture"


def test_scope_rejected_returns_to_discovery():
    assert route_scope(_state(scope_approved=False)) == "product_discovery"


def test_scope_exceeds_cycles_goes_to_human_review():
    state = _state(scope_approved=False, cycles={"scope": MAX_CYCLES})
    assert route_scope(state) == "human_review"


def test_code_review_changes_requested_loops_to_development():
    state = _state(stage_results={"code_review": {"status": "changes_requested"}})
    assert route_code_review(state) == "development"


def test_code_review_approved_moves_to_tests():
    state = _state(stage_results={"code_review": {"status": "approved"}})
    assert route_code_review(state) == "automated_tests"


def test_architecture_gate_limits_cycles():
    state = _state(
        stage_results={"architecture": {"status": "changes_requested"}},
        cycles={"architecture": MAX_CYCLES},
    )
    assert route_architecture_gate(state) == "human_review"
