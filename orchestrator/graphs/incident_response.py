"""Grafo de resposta a incidentes (esqueleto para evolução futura).

Fluxo: classificação -> mitigação -> causa raiz -> ações preventivas.
"""
from langgraph.graph import END, StateGraph

from orchestrator.state.state import DeliveryState


async def classify(state: DeliveryState) -> dict:
    return {"current_stage": "incident_classification"}


async def mitigate(state: DeliveryState) -> dict:
    return {"current_stage": "incident_mitigation"}


async def root_cause(state: DeliveryState) -> dict:
    return {"current_stage": "incident_root_cause"}


def build_graph(checkpointer=None):
    graph = StateGraph(DeliveryState)
    graph.add_node("classify", classify)
    graph.add_node("mitigate", mitigate)
    graph.add_node("root_cause", root_cause)
    graph.set_entry_point("classify")
    graph.add_edge("classify", "mitigate")
    graph.add_edge("mitigate", "root_cause")
    graph.add_edge("root_cause", END)
    return graph.compile(checkpointer=checkpointer)
