"""Métricas Prometheus (seção 19.2)."""
from prometheus_client import Counter, Gauge, Histogram

WORKFLOWS_STARTED = Counter("factory_workflows_started_total", "Workflows iniciados")
WORKFLOWS_COMPLETED = Counter("factory_workflows_completed_total", "Workflows concluídos")
WORKFLOWS_FAILED = Counter("factory_workflows_failed_total", "Workflows falhos")
STEP_DURATION = Histogram("factory_step_duration_seconds", "Duração por etapa", ["step"])
APPROVAL_WAIT = Gauge("factory_approvals_pending", "Aprovações pendentes")
AGENT_EXECUTIONS = Counter(
    "factory_agent_executions_total", "Execuções por agente", ["agent_id", "status"]
)
TOOL_CALLS = Counter("factory_tool_calls_total", "Chamadas de ferramentas", ["tool"])
