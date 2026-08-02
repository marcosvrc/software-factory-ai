"""Estado tipado do grafo de entrega de software.

O estado do LangGraph carrega apenas referências e resumos; a fonte de verdade
é o PostgreSQL (princípio 3.3). Limite de 3 ciclos por gate (seção 9.1).
"""
from typing import Annotated, Any, TypedDict


def _merge_dict(left: dict, right: dict) -> dict:
    return {**left, **right}


def _extend(left: list, right: list) -> list:
    return left + [item for item in right if item not in left]


def _merge_code_files(left: list[dict], right: list[dict]) -> list[dict]:
    """Mescla code_files por 'path': a versão mais nova (right) substitui a
    antiga do mesmo arquivo, preservando os demais."""
    by_path = {cf["path"]: cf for cf in left}
    for cf in right:
        by_path[cf["path"]] = cf
    return list(by_path.values())


def _merge_findings_by_stage(left: dict[str, list[dict]], right: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Substitui os findings de cada etapa presente em `right` (inclusive
    quando a lista é vazia — etapa sem findings nesta rodada), preservando
    findings de outras etapas intocados.

    Findings de code_review/tests/qa/security descrevem o estado do CÓDIGO
    NA RODADA em que foram gerados. Antes, `findings` era uma lista simples
    acumulada com _extend: findings de problemas já corrigidos continuavam
    para sempre em pending_findings, e o modelo os repetia como se fossem
    atuais em vez de revalidar o código presente no contexto — na execução
    7bc7aabf-c54e-43ba-ac79-452df2cd7365 os mesmos 5 findings de duplicação
    foram reportados por 6+ rodadas seguidas, mesmo com o código já
    corrigido, porque nada nunca os descartava. Usar um dict por etapa (em
    vez de inferir a etapa pelo conteúdo da lista) permite substituir
    corretamente mesmo quando a nova rodada não reporta nenhum finding."""
    return {**left, **right}


class DeliveryState(TypedDict, total=False):
    workflow_run_id: str
    project_id: str
    demand_id: str
    correlation_id: str

    demand_title: str
    demand_description: str
    # Respostas do solicitante às perguntas de esclarecimento levantadas pelo
    # product.intake-analyst (ver orchestrator/nodes/approvals.intake_clarification).
    # Realimentado na próxima execução do intake_analysis, até que a demanda
    # seja considerada suficientemente especificada ou os ciclos se esgotem.
    clarification_notes: Annotated[list[str], _extend]

    current_stage: str
    stage_results: Annotated[dict[str, Any], _merge_dict]
    artifacts: Annotated[list[str], _extend]
    # conteúdo real do código produzido pelos agentes de engineering; usado
    # como contexto factual pelos agentes seguintes (code review, testes,
    # segurança) em vez de nomes de arquivo sem conteúdo (ver
    # orchestrator/context_builder.py e workers/base/consumer.py).
    code_files: Annotated[list[dict], _merge_code_files]
    # Indexado por etapa (stage) que gerou os findings, não uma lista plana:
    # permite que cada etapa substitua completamente os SEUS findings a cada
    # rodada (inclusive esvaziando quando não há mais problemas), sem
    # acumular para sempre findings de rodadas anteriores já corrigidas.
    # Ver _merge_findings_by_stage e orchestrator.nodes.stages.all_findings.
    findings_by_stage: Annotated[dict[str, list[dict]], _merge_findings_by_stage]
    decisions: Annotated[list[dict], _extend]

    # contadores de ciclo por gate (seção 9.1: máximo 3, depois HUMAN_REVIEW_REQUIRED)
    cycles: Annotated[dict[str, int], _merge_dict]

    scope_approved: bool
    architecture_approved: bool
    release_approved: bool
    human_review_required: bool
    failure_reason: str

    # gate que esgotou os ciclos automáticos e escalou para human_review;
    # usado para retomar na etapa correta após aprovação (ver
    # orchestrator/graphs/software_delivery.py RESUME_AFTER_GATE).
    escalated_gate: str


def all_findings(state: DeliveryState) -> list[dict]:
    """Achata findings_by_stage em uma lista única, na ordem de inserção dos
    dicts (Python 3.7+ preserva ordem). Usado onde se precisa de todos os
    findings atuais sem distinção de etapa (ex.: lista de riscos numa
    aprovação humana)."""
    by_stage = state.get("findings_by_stage", {})
    return [f for stage_findings in by_stage.values() for f in stage_findings]
