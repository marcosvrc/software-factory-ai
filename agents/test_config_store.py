"""Testes da configuração efetiva de agentes (agents/config_store.py).

Contexto do bug estrutural corrigido: orquestrador e workers carregavam a
definição do agente apenas dos YAMLs em agents/definitions, então a tabela
`agent_definitions` (e a API/tela de configuração) não tinha efeito nenhum na
execução — desabilitar um agente ou trocar seu modelo/prompt não mudava nada.
Agora a configuração do banco é mesclada sobre o YAML base.
"""
from agents.config_store import merge_definition

BASE = {
    "id": "engineering.backend",
    "name": "Desenvolvedor Backend",
    "version": "1.0.0",
    "domain": "engineering",
    "objective": "objetivo original do YAML",
    "responsibilities": ["implementa serviços"],
    "inputs": {"required": ["technical_backlog"], "optional": []},
    "outputs": {"schema": "schemas/agent-result.schema.json"},
    "tools": {"allowed": ["repository.read"], "denied": ["shell.unrestricted"]},
    "model": {"provider": "ollama", "primary": "qwen2.5-coder", "temperature": 0.1},
    "quality_gates": ["build_success"],
    "retry": {"max_attempts": 2},
    "escalation": ["tech-lead"],
    "enabled": True,
}


def test_without_override_returns_base_definition():
    assert merge_definition(BASE, None) == BASE


def test_disabled_in_database_wins_over_yaml():
    """O toggle da tela precisa ter efeito real: `enabled` vem sempre da
    coluna do banco, nunca do YAML."""
    merged = merge_definition(BASE, {"enabled": False, "configuration": {}})
    assert merged["enabled"] is False


def test_partial_model_override_keeps_other_model_fields():
    """Editar apenas o modelo primário não deve apagar provider/temperature."""
    merged = merge_definition(
        BASE, {"enabled": True, "configuration": {"model": {"primary": "llama3.1"}}}
    )
    assert merged["model"]["primary"] == "llama3.1"
    assert merged["model"]["provider"] == "ollama"
    assert merged["model"]["temperature"] == 0.1


def test_objective_and_prompt_override_are_applied():
    merged = merge_definition(
        BASE,
        {
            "enabled": True,
            "configuration": {
                "objective": "objetivo customizado",
                "prompt_template": "Você é {agent_name}.",
            },
        },
    )
    assert merged["objective"] == "objetivo customizado"
    assert merged["prompt_template"] == "Você é {agent_name}."


def test_invalid_override_falls_back_to_base_instead_of_breaking_execution():
    """Se a configuração salva ficar inválida (campo obrigatório removido), a
    execução deve seguir com o YAML base em vez de falhar o pipeline."""
    merged = merge_definition(BASE, {"enabled": True, "configuration": {"tools": {}}})
    assert merged["tools"] == BASE["tools"]
    assert merged["enabled"] is True


def test_invalid_override_still_respects_disabled_flag():
    merged = merge_definition(BASE, {"enabled": False, "configuration": {"tools": {}}})
    assert merged["enabled"] is False


def test_agent_only_in_database_uses_database_configuration():
    """Agente sem YAML correspondente (criado apenas no banco) é utilizável se
    a configuração armazenada for completa."""
    config = {**BASE, "objective": "somente banco"}
    merged = merge_definition(None, {"enabled": True, "configuration": config})
    assert merged["objective"] == "somente banco"


def test_agent_only_in_database_with_incomplete_config_is_unusable():
    merged = merge_definition(None, {"enabled": True, "configuration": {"id": "x"}})
    assert merged is None
