"""Testes de roteamento e registry (seções 23.3 e 26.1)."""
from agents.registry import AgentRegistry, validate_definition
from orchestrator.routing.router import STAGE_AGENTS, CapabilityRouter, DOMAIN_QUEUE


def test_registry_loads_all_agents():
    registry = AgentRegistry.load_default()
    assert len(registry.all()) >= 50


def test_all_stage_agents_exist_in_registry():
    registry = AgentRegistry.load_default()
    for stage, agent_ids in STAGE_AGENTS.items():
        for agent_id in agent_ids:
            assert registry.get(agent_id) is not None, f"{agent_id} ausente ({stage})"


def test_router_returns_queue_by_domain():
    registry = AgentRegistry.load_default()
    router = CapabilityRouter(registry)
    definition = registry.get("engineering.backend")
    assert router.queue_for(definition) == "factory.engineering"
    assert set(DOMAIN_QUEUE.values()) == {
        "factory.product", "factory.architecture", "factory.engineering",
        "factory.validation", "factory.security", "factory.operations",
        "factory.delivery", "factory.governance",
    }


def test_definition_validation_rejects_incomplete():
    import pytest
    from shared.exceptions import AgentDefinitionError

    with pytest.raises(AgentDefinitionError):
        validate_definition({"id": "x", "name": "X"})
