"""Estado tipado do grafo de entrega de software.

O estado do LangGraph carrega apenas referências e resumos; a fonte de verdade
é o PostgreSQL (princípio 3.3). Limite de 3 ciclos por gate (seção 9.1).
"""
from typing import Annotated, Any, TypedDict


def _merge_dict(left: dict, right: dict) -> dict:
    return {**left, **right}


def _extend(left: list, right: list) -> list:
    return left + [item for item in right if item not in left]


class DeliveryState(TypedDict, total=False):
    workflow_run_id: str
    project_id: str
    demand_id: str
    correlation_id: str

    demand_title: str
    demand_description: str

    current_stage: str
    stage_results: Annotated[dict[str, Any], _merge_dict]
    artifacts: Annotated[list[str], _extend]
    findings: Annotated[list[dict], _extend]
    decisions: Annotated[list[dict], _extend]

    # contadores de ciclo por gate (seção 9.1: máximo 3, depois HUMAN_REVIEW_REQUIRED)
    cycles: Annotated[dict[str, int], _merge_dict]

    scope_approved: bool
    architecture_approved: bool
    release_approved: bool
    human_review_required: bool
    failure_reason: str
