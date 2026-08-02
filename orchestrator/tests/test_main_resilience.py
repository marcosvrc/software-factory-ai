"""Testes de resiliência do orquestrador (orchestrator/main.py).

Cobrem os dois problemas identificados na execução 14b9cea1:
1. queda momentânea do Postgres no meio de uma execução;
2. runs órfãs presas em RUNNING sem nenhum worker local ativo.
"""
from types import SimpleNamespace

import pytest

from orchestrator import main as orchestrator_main


class _FakeCheckpointer:
    """Substitui o AsyncPostgresSaver real: rastreia se aget_tuple já
    retornaria um checkpoint para o thread_id, sem depender de Postgres."""

    def __init__(self, has_checkpoint: bool = False):
        self.has_checkpoint = has_checkpoint

    async def aget_tuple(self, config):
        return SimpleNamespace() if self.has_checkpoint else None


@pytest.fixture(autouse=True)
def _reset_running_set():
    orchestrator_main._running.clear()
    yield
    orchestrator_main._running.clear()


async def test_run_workflow_marks_completed_on_success(monkeypatch):
    async def fake_ainvoke(invoke_input, config):
        assert invoke_input is not None  # sem checkpoint prévio, roda do zero
        return {"current_stage": "delivered"}

    fake_graph = SimpleNamespace(ainvoke=fake_ainvoke)
    monkeypatch.setattr(orchestrator_main, "build_graph", lambda checkpointer: fake_graph)
    monkeypatch.setattr(orchestrator_main, "_checkpointer", _FakeCheckpointer())

    calls = []

    async def fake_mark_status(run_id, **values):
        calls.append(values)

    monkeypatch.setattr(orchestrator_main, "_mark_run_status", fake_mark_status)
    monkeypatch.setattr(orchestrator_main.db, "record_audit_event", _noop_async)

    run = {"workflow_run_id": "run-1", "correlation_id": "corr-1"}
    await orchestrator_main.run_workflow(run)

    statuses = [c["status"] for c in calls]
    assert statuses == ["RUNNING", "COMPLETED"]


async def test_run_workflow_resumes_with_none_when_checkpoint_exists(monkeypatch):
    """Regressão principal: se já existe checkpoint para o thread_id e
    resume=True, o grafo deve ser invocado com None (retomar), não com o
    estado completo (que reiniciaria a execução do zero)."""
    received_inputs = []

    async def fake_ainvoke(invoke_input, config):
        received_inputs.append(invoke_input)
        return {"current_stage": "delivered"}

    fake_graph = SimpleNamespace(ainvoke=fake_ainvoke)
    monkeypatch.setattr(orchestrator_main, "build_graph", lambda checkpointer: fake_graph)
    monkeypatch.setattr(orchestrator_main, "_checkpointer", _FakeCheckpointer(has_checkpoint=True))
    monkeypatch.setattr(orchestrator_main, "_mark_run_status", _noop_async_kwargs)
    monkeypatch.setattr(orchestrator_main.db, "record_audit_event", _noop_async)

    run = {"workflow_run_id": "run-2", "correlation_id": "corr-2"}
    await orchestrator_main.run_workflow(run, resume=True)

    assert received_inputs == [None]


async def test_run_workflow_does_not_resume_without_checkpoint_even_if_flagged(monkeypatch):
    """Caso de borda: resume=True mas o checkpointer não tem nada salvo para
    esse thread_id (ex.: MemorySaver perdeu o estado ao reiniciar). Deve
    recomeçar do zero em vez de chamar ainvoke(None, ...), que levantaria
    EmptyInputError."""
    received_inputs = []

    async def fake_ainvoke(invoke_input, config):
        received_inputs.append(invoke_input)
        return {"current_stage": "delivered"}

    fake_graph = SimpleNamespace(ainvoke=fake_ainvoke)
    monkeypatch.setattr(orchestrator_main, "build_graph", lambda checkpointer: fake_graph)
    monkeypatch.setattr(orchestrator_main, "_checkpointer", _FakeCheckpointer(has_checkpoint=False))
    monkeypatch.setattr(orchestrator_main, "_mark_run_status", _noop_async_kwargs)
    monkeypatch.setattr(orchestrator_main.db, "record_audit_event", _noop_async)

    run = {"workflow_run_id": "run-3", "correlation_id": "corr-3", "demand_title": "x"}
    await orchestrator_main.run_workflow(run, resume=True)

    assert received_inputs[0] is not None
    assert received_inputs[0]["workflow_run_id"] == "run-3"


async def test_run_workflow_survives_when_failure_status_update_also_fails(monkeypatch):
    """Regressão: se o workflow falha E a gravação do status de falha também
    falha (Postgres ainda em recovery), run_workflow não deve propagar a
    exceção — apenas logar e deixar _reconcile_stale_running_runs tentar de
    novo no próximo ciclo de polling."""

    async def fake_ainvoke(invoke_input, config):
        raise RuntimeError("agent execution failed")

    fake_graph = SimpleNamespace(ainvoke=fake_ainvoke)
    monkeypatch.setattr(orchestrator_main, "build_graph", lambda checkpointer: fake_graph)
    monkeypatch.setattr(orchestrator_main, "_checkpointer", _FakeCheckpointer())

    async def always_fails(run_id, **values):
        raise ConnectionError("database system is in recovery mode")

    monkeypatch.setattr(orchestrator_main, "_mark_run_status", always_fails)

    run = {"workflow_run_id": "run-4", "correlation_id": "corr-4"}
    # Não deve levantar excecão até o chamador.
    await orchestrator_main.run_workflow(run)
    assert "run-4" not in orchestrator_main._running


async def test_reconcile_stale_running_runs_schedules_resume(monkeypatch):
    resumed = []

    async def fake_fetch_stale():
        return [{"workflow_run_id": "run-5", "correlation_id": "corr-5"}]

    async def fake_run_workflow(run, resume=False):
        resumed.append((run["workflow_run_id"], resume))

    monkeypatch.setattr(orchestrator_main.db, "fetch_stale_running_runs", fake_fetch_stale)
    monkeypatch.setattr(orchestrator_main, "run_workflow", fake_run_workflow)

    await orchestrator_main._reconcile_stale_running_runs()
    # asyncio.create_task agenda mas não espera; aguardamos o loop processar.
    import asyncio

    await asyncio.sleep(0)
    assert resumed == [("run-5", True)]


async def test_reconcile_skips_runs_already_tracked_locally(monkeypatch):
    """Uma run já em _running (processo local ativo, só demorada) não deve
    ser 'roubada' e reprocessada em paralelo."""
    orchestrator_main._running.add("run-6")

    async def fake_fetch_stale():
        return [{"workflow_run_id": "run-6", "correlation_id": "corr-6"}]

    called = False

    async def fake_run_workflow(run, resume=False):
        nonlocal called
        called = True

    monkeypatch.setattr(orchestrator_main.db, "fetch_stale_running_runs", fake_fetch_stale)
    monkeypatch.setattr(orchestrator_main, "run_workflow", fake_run_workflow)

    await orchestrator_main._reconcile_stale_running_runs()
    import asyncio

    await asyncio.sleep(0)
    assert called is False


async def test_reconcile_does_not_race_with_live_approval_polling(monkeypatch):
    """Regressão: orchestrator/nodes/approvals._wait_for_approval não
    atualiza updated_at enquanto aguarda decisão humana (só faz SELECT), então
    uma run legitimamente em WAITING_HUMAN por mais que
    STALE_RUNNING_THRESHOLD_SECONDS pareceria órfã para uma query baseada só
    em tempo. A proteção correta é `_running`: enquanto a task run_workflow
    do processo atual estiver viva (bloqueada esperando a aprovação), ela
    continua marcada em _running e não deve ser reprocessada em paralelo."""
    orchestrator_main._running.add("run-7")

    async def fake_fetch_stale():
        # Mesmo que o banco não tenha atualizado updated_at há muito tempo,
        # a query devolveria essa run como candidata.
        return [{"workflow_run_id": "run-7", "correlation_id": "corr-7"}]

    called = False

    async def fake_run_workflow(run, resume=False):
        nonlocal called
        called = True

    monkeypatch.setattr(orchestrator_main.db, "fetch_stale_running_runs", fake_fetch_stale)
    monkeypatch.setattr(orchestrator_main, "run_workflow", fake_run_workflow)

    await orchestrator_main._reconcile_stale_running_runs()
    import asyncio

    await asyncio.sleep(0)
    assert called is False, (
        "uma run com processo local ativo nunca deve ser retomada em paralelo"
    )


async def _noop_async(*args, **kwargs):
    return None


async def _noop_async_kwargs(run_id, **kwargs):
    return None
