"""Testes do gate de esclarecimento de intake (orchestrator/nodes/approvals.
intake_clarification).

Contexto: quando product.intake-analyst identifica lacunas na demanda (canal,
escopo, volume, comportamentos essenciais, restrições não-funcionais, dados
sensíveis, integrações, critérios de sucesso), o agente não pode resolver a
lacuna por conta própria — só o solicitante sabe responder. Este gate pausa a
execução, pede a resposta via aprovação e a incorpora em clarification_notes.
"""
from orchestrator.nodes.approvals import intake_clarification


def _state(**kw):
    base = {
        "workflow_run_id": "run-1",
        "correlation_id": "corr-1",
        "demand_title": "Criar cadastro de produtos",
        "stage_results": {},
        "cycles": {},
    }
    base.update(kw)
    return base


async def test_intake_clarification_incorporates_rationale_into_notes(monkeypatch):
    async def fake_create_approval(**kwargs):
        assert kwargs["approval_type"] == "intake_clarification"
        return "approval-1"

    async def fake_wait_for_approval(approval_id):
        return "APPROVED"

    async def fake_get_rationale(approval_id):
        return "Canal: apenas web. Escopo: backend e frontend. Volume: ~500 usuários/dia."

    monkeypatch.setattr("orchestrator.nodes.approvals.db.create_approval", fake_create_approval)
    monkeypatch.setattr("orchestrator.nodes.approvals.db.update_run", _noop)
    monkeypatch.setattr("orchestrator.nodes.approvals.db.record_audit_event", _noop)
    monkeypatch.setattr("orchestrator.nodes.approvals.db.record_decision", _noop)
    monkeypatch.setattr(
        "orchestrator.nodes.approvals._wait_for_approval", fake_wait_for_approval
    )
    monkeypatch.setattr(
        "orchestrator.nodes.approvals.db.get_approval_rationale", fake_get_rationale
    )

    state = _state(
        stage_results={
            "intake_analysis": {
                "status": "changes_requested",
                "results": [
                    {
                        "findings": [
                            {
                                "category": "informacao_ausente",
                                "description": "Qual o canal de acesso?",
                            }
                        ]
                    }
                ],
            }
        }
    )
    update = await intake_clarification(state)

    assert update["clarification_notes"] == [
        "Canal: apenas web. Escopo: backend e frontend. Volume: ~500 usuários/dia."
    ]
    assert update["cycles"] == {"intake": 1}
    assert "human_review_required" not in update


async def test_intake_clarification_rejected_forces_human_review(monkeypatch):
    async def fake_create_approval(**kwargs):
        return "approval-2"

    async def fake_wait_for_approval(approval_id):
        return "REJECTED"

    monkeypatch.setattr("orchestrator.nodes.approvals.db.create_approval", fake_create_approval)
    monkeypatch.setattr("orchestrator.nodes.approvals.db.update_run", _noop)
    monkeypatch.setattr("orchestrator.nodes.approvals.db.record_audit_event", _noop)
    monkeypatch.setattr("orchestrator.nodes.approvals.db.record_decision", _noop)
    monkeypatch.setattr(
        "orchestrator.nodes.approvals._wait_for_approval", fake_wait_for_approval
    )
    monkeypatch.setattr(
        "orchestrator.nodes.approvals.db.get_approval_rationale", lambda *_: _return_none()
    )

    state = _state()
    update = await intake_clarification(state)

    assert update["human_review_required"] is True


async def test_intake_clarification_increments_cycle_counter(monkeypatch):
    """Regressão: o contador de ciclos do gate 'intake' precisa ser
    incrementado a cada rodada de esclarecimento, senão route_intake_analysis
    nunca escala para intake_escalate e o solicitante fica sendo questionado
    para sempre sem limite."""

    async def fake_create_approval(**kwargs):
        return "approval-3"

    async def fake_wait_for_approval(approval_id):
        return "APPROVED"

    async def fake_get_rationale(approval_id):
        return "resposta parcial"

    monkeypatch.setattr("orchestrator.nodes.approvals.db.create_approval", fake_create_approval)
    monkeypatch.setattr("orchestrator.nodes.approvals.db.update_run", _noop)
    monkeypatch.setattr("orchestrator.nodes.approvals.db.record_audit_event", _noop)
    monkeypatch.setattr("orchestrator.nodes.approvals.db.record_decision", _noop)
    monkeypatch.setattr(
        "orchestrator.nodes.approvals._wait_for_approval", fake_wait_for_approval
    )
    monkeypatch.setattr(
        "orchestrator.nodes.approvals.db.get_approval_rationale", fake_get_rationale
    )

    state = _state(cycles={"intake": 1})
    update = await intake_clarification(state)
    assert update["cycles"] == {"intake": 2}


async def _noop(*args, **kwargs):
    return None


async def _return_none():
    return None
