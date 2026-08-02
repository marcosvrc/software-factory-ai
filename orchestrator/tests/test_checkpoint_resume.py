"""Testes de regressão para retomada de execução via checkpoint.

Contexto: sem checkpointer, qualquer restart do orchestrator ou queda
momentânea do Postgres durante uma execução perdia todo o progresso — a
única saída era reprocessar a demanda do zero (ver histórico da execução
14b9cea1, que ficou presa em RUNNING após o Postgres reiniciar no meio de
`product_discovery`).

Estes testes usam um grafo mínimo com MemorySaver para validar o
comportamento de retomada de forma isolada e rápida (sem depender de
Postgres real), replicando o experimento que confirmou o comportamento do
LangGraph antes da implementação em orchestrator/main.py.
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict


class _State(TypedDict, total=False):
    steps: list[str]


def _build_flaky_graph(call_counter: dict):
    """Grafo a -> b -> c, onde 'b' falha na primeira execução (simula uma
    queda de conexão com o banco no meio de uma etapa)."""

    async def a(state: _State) -> dict:
        return {"steps": state.get("steps", []) + ["a"]}

    async def b(state: _State) -> dict:
        call_counter["b"] = call_counter.get("b", 0) + 1
        if call_counter["b"] == 1:
            raise RuntimeError("simulated transient failure")
        return {"steps": state.get("steps", []) + ["b"]}

    async def c(state: _State) -> dict:
        return {"steps": state.get("steps", []) + ["c"]}

    graph = StateGraph(_State)
    graph.add_node("a", a)
    graph.add_node("b", b)
    graph.add_node("c", c)
    graph.set_entry_point("a")
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", END)
    return graph.compile(checkpointer=MemorySaver())


async def test_resume_with_checkpoint_does_not_reexecute_completed_nodes():
    """Regressão principal: com checkpoint, retomar após falha deve pular
    nós já concluídos (aqui, 'a') e reexecutar apenas o nó que falhou."""
    call_counter: dict = {}
    graph = _build_flaky_graph(call_counter)
    config = {"configurable": {"thread_id": "run-1"}}

    raised = False
    try:
        await graph.ainvoke({"steps": []}, config=config)
    except RuntimeError:
        raised = True
    assert raised, "a primeira execução deveria falhar no nó 'b'"

    # Retomada: passar None reaproveita o checkpoint salvo antes da falha.
    result = await graph.ainvoke(None, config=config)
    assert result["steps"] == ["a", "b", "c"]
    # 'a' não deve ter sido contabilizado de novo (não há contador para ele,
    # mas o resultado confirma que não duplicou "a" na lista).
    assert result["steps"].count("a") == 1


async def test_ainvoke_none_without_checkpoint_raises_empty_input():
    """Caso de borda que motivou a checagem explícita de checkpoint em
    orchestrator/main.py.run_workflow: sem checkpoint prévio para o
    thread_id (ex.: fallback MemorySaver que perdeu o estado ao reiniciar o
    processo), ainvoke(None, ...) falha em vez de simplesmente não fazer
    nada — por isso run_workflow precisa verificar aget_tuple() antes de
    decidir entre None e o estado completo."""
    call_counter: dict = {}
    graph = _build_flaky_graph(call_counter)
    config = {"configurable": {"thread_id": "thread-nunca-executado"}}

    raised_empty_input = False
    try:
        await graph.ainvoke(None, config=config)
    except Exception as exc:  # noqa: BLE001
        raised_empty_input = type(exc).__name__ == "EmptyInputError"
    assert raised_empty_input
