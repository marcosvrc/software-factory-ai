"""Testes dos helpers da API de configuração de agentes.

Valida a proteção contra salvar uma configuração incompleta pela tela — o que
faria o worker rejeitar o agente em tempo de execução ("agente não encontrado
ou desabilitado") — e a marcação de "customizado" usada pela UI.
"""
import pytest
from fastapi import HTTPException

from app.api.v1.agents import _validate_configuration, _to_out

VALID = {
    "id": "engineering.backend",
    "name": "Desenvolvedor Backend",
    "version": "1.0.0",
    "domain": "engineering",
    "objective": "objetivo",
    "inputs": {"required": ["x"], "optional": []},
    "outputs": {"schema": "schemas/agent-result.schema.json"},
    "tools": {"allowed": ["repository.read"], "denied": []},
    "model": {"provider": "ollama", "primary": "qwen2.5-coder"},
    "quality_gates": ["build_success"],
    "retry": {"max_attempts": 2},
    "escalation": ["tech-lead"],
}


class _Agent:
    def __init__(self, configuration, default_configuration, **kw):
        self.id = kw.get("id", "engineering.backend")
        self.name = kw.get("name", "Desenvolvedor Backend")
        self.version = kw.get("version", "1.0.0")
        self.domain = kw.get("domain", "engineering")
        self.configuration = configuration
        self.default_configuration = default_configuration
        self.enabled = kw.get("enabled", True)
        self.stages = kw.get("stages", ["development"])


def test_valid_configuration_passes():
    _validate_configuration(VALID)


@pytest.mark.parametrize("missing_field", ["objective", "model", "tools", "quality_gates"])
def test_missing_required_field_is_rejected(missing_field):
    config = {k: v for k, v in VALID.items() if k != missing_field}
    with pytest.raises(HTTPException) as exc:
        _validate_configuration(config)
    assert exc.value.status_code == 422


def test_tools_without_allowed_and_denied_is_rejected():
    with pytest.raises(HTTPException) as exc:
        _validate_configuration({**VALID, "tools": {}})
    assert exc.value.status_code == 422


def test_inputs_without_required_is_rejected():
    with pytest.raises(HTTPException) as exc:
        _validate_configuration({**VALID, "inputs": {}})
    assert exc.value.status_code == 422


def test_outputs_without_schema_is_rejected():
    with pytest.raises(HTTPException) as exc:
        _validate_configuration({**VALID, "outputs": {}})
    assert exc.value.status_code == 422


def test_agent_equal_to_default_is_not_marked_customized():
    out = _to_out(_Agent(configuration=dict(VALID), default_configuration=dict(VALID)))
    assert out.customized is False


def test_agent_differing_from_default_is_marked_customized():
    customized = {**VALID, "objective": "objetivo editado na tela"}
    out = _to_out(_Agent(configuration=customized, default_configuration=dict(VALID)))
    assert out.customized is True
    assert out.stages == ["development"]
