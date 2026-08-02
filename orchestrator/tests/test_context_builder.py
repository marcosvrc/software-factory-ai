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


def test_code_files_are_included_and_limited():
    """Regressão: sem code_files reais no contexto, agentes de revisão/teste
    não têm nada concreto para avaliar e alucinam findings genéricos."""
    files = [{"path": f"f{i}.py", "content": "x"} for i in range(20)]
    context = _build(code_files=files)
    assert len(context["code_files"]) <= 15


def test_code_files_content_is_truncated():
    files = [{"path": "big.py", "content": "x" * 100_000}]
    context = _build(code_files=files)
    assert len(context["code_files"][0]["content"]) < 100_000


def test_code_files_default_empty():
    assert _build()["code_files"] == []
