"""Testes da resolução de agentes por etapa com a configuração efetiva.

Regressão estrutural: a seleção de agentes usava apenas os YAMLs em disco
(CapabilityRouter/AgentRegistry), então desabilitar um agente na tela de
configuração não tinha nenhum efeito na execução. Agora cada agente da etapa
é resolvido contra a configuração do banco e os desabilitados são ignorados.
"""
from orchestrator.nodes import stages


def _definition(agent_id: str, enabled: bool = True) -> dict:
    return {"id": agent_id, "name": agent_id, "enabled": enabled}


async def test_disabled_agent_is_excluded_from_stage(monkeypatch):
    monkeypatch.setattr(
        stages._router,
        "agents_for_stage",
        lambda stage: [_definition("product.product-manager"), _definition("product.product-owner")],
    )

    async def fake_effective(base, agent_id):
        return _definition(agent_id, enabled=agent_id != "product.product-owner")

    monkeypatch.setattr(stages, "effective_definition", fake_effective)

    resolved = await stages._resolve_stage_agents("product_discovery")
    assert [d["id"] for d in resolved] == ["product.product-manager"]


async def test_all_agents_enabled_are_kept(monkeypatch):
    monkeypatch.setattr(
        stages._router,
        "agents_for_stage",
        lambda stage: [_definition("a"), _definition("b")],
    )

    async def fake_effective(base, agent_id):
        return _definition(agent_id)

    monkeypatch.setattr(stages, "effective_definition", fake_effective)

    resolved = await stages._resolve_stage_agents("development")
    assert [d["id"] for d in resolved] == ["a", "b"]


async def test_unresolvable_agent_is_skipped(monkeypatch):
    """Configuração inválida a ponto de não produzir definição usável não deve
    quebrar a etapa — o agente é apenas ignorado."""
    monkeypatch.setattr(stages._router, "agents_for_stage", lambda stage: [_definition("a")])

    async def fake_effective(base, agent_id):
        return None

    monkeypatch.setattr(stages, "effective_definition", fake_effective)

    assert await stages._resolve_stage_agents("development") == []


async def test_stage_without_agents_is_approved_automatically(monkeypatch):
    """Quando todos os agentes de uma etapa estão desabilitados, a etapa é
    aprovada automaticamente em vez de travar o fluxo."""
    monkeypatch.setattr(stages._router, "agents_for_stage", lambda stage: [_definition("a")])

    async def fake_effective(base, agent_id):
        return _definition("a", enabled=False)

    monkeypatch.setattr(stages, "effective_definition", fake_effective)

    result = await stages._run_stage({"workflow_run_id": "r1", "correlation_id": "c1"}, "code_review")
    assert result["stage_results"]["code_review"]["status"] == "approved"
