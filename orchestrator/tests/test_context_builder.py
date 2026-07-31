"""Testes do context builder (política 14.3)."""
from orchestrator.context_builder import build_context


def _build(**overrides):
    params = dict(
        objective="obj",
        required_inputs={"demand": "x", "api_password": "secreta"},
        relevant_artifacts=[f"a{i}" for i in range(50)],
        applicable_decisions=[],
        pending_findings=[],
        constraints=["local"],
        allowed_tools=["artifact.read"],
        response_schema={},
    )
    params.update(overrides)
    return build_context(**params)


def test_secrets_are_stripped():
    context = _build()
    assert context["required_inputs"]["api_password"] == "[removido]"


def test_artifacts_are_limited():
    assert len(_build()["relevant_artifacts"]) <= 20


def test_long_fields_truncated():
    context = _build(objective="x" * 10_000)
    assert len(context["objective"]) < 10_000
