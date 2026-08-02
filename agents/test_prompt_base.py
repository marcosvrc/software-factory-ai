"""Testes de regressão do prompt base (agents/prompts/base.txt).

Regressão real: uma chave literal '{"path", "content"}' no texto do prompt
foi interpretada pelo str.format() como placeholder, causando KeyError em
TODA execução de agente (worker travava com attempt=max_attempts sem nunca
completar a tarefa). Ver agents/runtime/executor.build_system_prompt.
"""
from agents.runtime.executor import build_system_prompt

MINIMAL_DEFINITION = {
    "name": "Agente Teste",
    "version": "1.0.0",
    "objective": "objetivo de teste",
    "responsibilities": ["r1", "r2"],
    "inputs": {"required": ["x"], "optional": []},
    "constraints": [],
    "tools": {"allowed": ["artifact.read"]},
    "quality_gates": ["gate1"],
}


def test_build_system_prompt_does_not_raise_keyerror():
    """Regressão: chaves literais no texto do prompt (ex.: exemplos de JSON
    como {"path": ...}) quebram o str.format() usado para injetar as
    variáveis do agente. O prompt deve usar apenas os placeholders
    esperados: {agent_name}, {agent_version}, {objective},
    {responsibilities}, {input_manifest}, {constraints}, {allowed_tools},
    {quality_gates}."""
    prompt = build_system_prompt(MINIMAL_DEFINITION, context={"constraints": []})
    assert "Agente Teste" in prompt
    assert "objetivo de teste" in prompt


def test_build_system_prompt_includes_all_sections():
    prompt = build_system_prompt(MINIMAL_DEFINITION, context={"constraints": ["c1"]})
    assert "r1" in prompt
    assert "artifact.read" in prompt
    assert "gate1" in prompt
    assert "c1" in prompt


def test_build_system_prompt_includes_anti_duplication_rule():
    """Regressão funcional: sem uma instrução explícita, o modelo local
    reintroduzia o mesmo método/rota duplicado a cada rodada de code_review
    (ver execução 7bc7aabf: StockService.create/update/delete/get_by_id
    duplicados em 14 rodadas consecutivas, sem nunca convergir). O prompt
    precisa instruir o agente a editar o arquivo existente em vez de
    reescrevê-lo, e a tratar reintrodução de uma duplicação já apontada em
    pending_findings como falha grave."""
    prompt = build_system_prompt(MINIMAL_DEFINITION, context={"constraints": []})
    assert "PROIBIDO DUPLICAR" in prompt
    assert "pending_findings" in prompt
    assert "falha grave" in prompt


def test_custom_prompt_template_replaces_base_template():
    """Prompt customizado por agente (tela de configuração) substitui o
    template base, com os placeholders devidamente interpolados."""
    definition = {**MINIMAL_DEFINITION, "prompt_template": "Sou {agent_name} v{agent_version}."}
    prompt = build_system_prompt(definition, context={"constraints": []})
    assert prompt == "Sou Agente Teste v1.0.0."


def test_blank_custom_prompt_falls_back_to_base_template():
    definition = {**MINIMAL_DEFINITION, "prompt_template": "   "}
    prompt = build_system_prompt(definition, context={"constraints": []})
    assert "REGRAS" in prompt


def test_custom_prompt_with_json_braces_does_not_raise():
    """Regressão: com str.format(), um prompt contendo exemplo de JSON
    (chaves literais) levantava KeyError e derrubava TODA execução do agente.
    A renderização substitui apenas os placeholders conhecidos."""
    definition = {
        **MINIMAL_DEFINITION,
        "prompt_template": 'Responda {"path": "x", "content": "y"} para {agent_name}.',
    }
    prompt = build_system_prompt(definition, context={"constraints": []})
    assert '{"path": "x", "content": "y"}' in prompt
    assert "Agente Teste" in prompt


def test_build_system_prompt_instructs_revalidating_findings_against_current_code():
    """Regressão real: mesmo depois do backend corrigir a duplicação (código
    real no MinIO já sem o problema), o engineering.code-reviewer continuou
    reportando os MESMOS 5 findings de rodadas anteriores por 6+ vezes
    seguidas, sem nunca reavaliar o conteúdo atual. Causa raiz combinada com
    o bug estrutural corrigido em orchestrator/state/state.py
    (findings_by_stage): o prompt também precisa deixar explícito que
    pending_findings é uma hipótese da rodada anterior a ser CONFERIDA contra
    code_files atual, não um fato a ser repetido."""
    prompt = build_system_prompt(MINIMAL_DEFINITION, context={"constraints": []})
    assert "reabrir o arquivo correspondente" in prompt
    assert "não o reporte de novo" in prompt.lower()
