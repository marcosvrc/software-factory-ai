"""Testes dos reducers de code_files e findings no estado do grafo (DeliveryState)."""
from orchestrator.state.state import _merge_code_files, _merge_findings_by_stage, all_findings


def test_merge_keeps_files_with_distinct_paths():
    left = [{"path": "a.py", "content": "1"}]
    right = [{"path": "b.py", "content": "2"}]
    merged = _merge_code_files(left, right)
    assert {cf["path"] for cf in merged} == {"a.py", "b.py"}


def test_merge_replaces_same_path_with_newer_version():
    """Regressão: quando um agente reenvia um arquivo já existente (ex.: após
    changes_requested), a versão mais nova deve substituir a antiga, não
    duplicar nem manter o conteúdo desatualizado."""
    left = [{"path": "a.py", "content": "old"}]
    right = [{"path": "a.py", "content": "new"}]
    merged = _merge_code_files(left, right)
    assert len(merged) == 1
    assert merged[0]["content"] == "new"


def test_merge_with_empty_right_keeps_left():
    left = [{"path": "a.py", "content": "1"}]
    assert _merge_code_files(left, []) == left


def test_merge_with_empty_left_returns_right():
    right = [{"path": "a.py", "content": "1"}]
    assert _merge_code_files([], right) == right


def test_findings_by_stage_replaces_same_stage_instead_of_accumulating():
    """Regressão real (execução 7bc7aabf-c54e-43ba-ac79-452df2cd7365): com
    findings acumulados numa lista simples (_extend), os 5 findings de
    duplicação da 1a rodada de code_review nunca eram descartados e
    continuavam sendo enviados como contexto para TODA rodada seguinte,
    mesmo depois do backend já ter corrigido o código — o agente reportava
    o mesmo problema por 14+ rodadas, sem nunca convergir porque a run
    nunca "esquecia" findings resolvidos. Indexar por etapa permite
    substituir completamente os findings de UMA etapa a cada rodada."""
    left = {
        "code_review": [{"id": "1", "description": "duplicado"}],
        "security_compliance": [{"id": "2", "description": "risco de segurança"}],
    }
    right = {"code_review": [{"id": "3", "description": "outro problema"}]}
    merged = _merge_findings_by_stage(left, right)
    assert merged == {
        "code_review": [{"id": "3", "description": "outro problema"}],
        "security_compliance": [{"id": "2", "description": "risco de segurança"}],
    }


def test_findings_by_stage_resolved_clears_old_findings():
    """Quando uma etapa não reporta mais nenhum finding, a rodada envia
    lista vazia para AQUELA etapa — e ela deve ser esvaziada de fato, não
    ignorada (diferente do bug original, onde não havia forma de expressar
    'esta etapa não tem mais findings')."""
    left = {"code_review": [{"id": "1", "description": "duplicado"}]}
    merged = _merge_findings_by_stage(left, {"code_review": []})
    assert merged == {"code_review": []}


def test_findings_by_stage_with_empty_left_returns_right():
    right = {"code_review": [{"id": "1"}]}
    assert _merge_findings_by_stage({}, right) == right


def test_all_findings_flattens_across_stages():
    state = {
        "findings_by_stage": {
            "code_review": [{"id": "1"}],
            "security_compliance": [{"id": "2"}, {"id": "3"}],
        }
    }
    assert all_findings(state) == [{"id": "1"}, {"id": "2"}, {"id": "3"}]


def test_all_findings_with_no_findings_by_stage_returns_empty_list():
    assert all_findings({}) == []
