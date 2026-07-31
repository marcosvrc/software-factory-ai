"""Grafo de revisão de arquitetura (esqueleto para evolução futura)."""
from langgraph.graph import END, StateGraph

from orchestrator.nodes import stages
from orchestrator.state.state import DeliveryState


def build_graph(checkpointer=None):
    graph = StateGraph(DeliveryState)
    graph.add_node("architecture", stages.architecture)
    graph.set_entry_point("architecture")
    graph.add_edge("architecture", END)
    return graph.compile(checkpointer=checkpointer)
