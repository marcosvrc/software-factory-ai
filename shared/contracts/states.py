"""Máquinas de estado (seção 10 da proposta).

Regras (seção 10.4):
- somente o orquestrador altera o estado global;
- workers alteram apenas o status de sua execução;
- toda transição gera um evento de auditoria;
- transições inválidas devem retornar erro;
- tarefa concluída não pode ser alterada sem nova versão;
- cancelamento não apaga histórico ou artefatos.
"""
from shared.utils.compat import StrEnum


class ProjectStatus(StrEnum):
    DRAFT = "DRAFT"
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


class RunStatus(StrEnum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_TOOL = "WAITING_TOOL"
    WAITING_AGENT = "WAITING_AGENT"
    WAITING_HUMAN = "WAITING_HUMAN"
    RETRYING = "RETRYING"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    COMPLETED = "COMPLETED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_FINAL = "FAILED_FINAL"
    CANCELLED = "CANCELLED"


class TaskStatus(StrEnum):
    BACKLOG = "BACKLOG"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    IN_TEST = "IN_TEST"
    SECURITY_REVIEW = "SECURITY_REVIEW"
    OPERATIONAL_REVIEW = "OPERATIONAL_REVIEW"
    READY_FOR_RELEASE = "READY_FOR_RELEASE"
    DONE = "DONE"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ApprovalStatus(StrEnum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


PROJECT_TRANSITIONS: dict[ProjectStatus, set[ProjectStatus]] = {
    ProjectStatus.DRAFT: {ProjectStatus.PLANNING, ProjectStatus.CANCELLED},
    ProjectStatus.PLANNING: {ProjectStatus.ACTIVE, ProjectStatus.BLOCKED, ProjectStatus.CANCELLED},
    ProjectStatus.ACTIVE: {
        ProjectStatus.WAITING_APPROVAL,
        ProjectStatus.BLOCKED,
        ProjectStatus.COMPLETED,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.WAITING_APPROVAL: {
        ProjectStatus.ACTIVE,
        ProjectStatus.BLOCKED,
        ProjectStatus.CANCELLED,
    },
    ProjectStatus.BLOCKED: {ProjectStatus.ACTIVE, ProjectStatus.CANCELLED},
    ProjectStatus.COMPLETED: {ProjectStatus.ARCHIVED},
    ProjectStatus.CANCELLED: {ProjectStatus.ARCHIVED},
    ProjectStatus.ARCHIVED: set(),
}

RUN_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.CREATED: {RunStatus.QUEUED, RunStatus.CANCELLED},
    RunStatus.QUEUED: {RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.RUNNING: {
        RunStatus.WAITING_TOOL,
        RunStatus.WAITING_AGENT,
        RunStatus.WAITING_HUMAN,
        RunStatus.RETRYING,
        RunStatus.PARTIALLY_COMPLETED,
        RunStatus.COMPLETED,
        RunStatus.FAILED_RETRYABLE,
        RunStatus.FAILED_FINAL,
        RunStatus.CANCELLED,
    },
    RunStatus.WAITING_TOOL: {RunStatus.RUNNING, RunStatus.FAILED_RETRYABLE, RunStatus.CANCELLED},
    RunStatus.WAITING_AGENT: {RunStatus.RUNNING, RunStatus.FAILED_RETRYABLE, RunStatus.CANCELLED},
    RunStatus.WAITING_HUMAN: {RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.RETRYING: {RunStatus.RUNNING, RunStatus.FAILED_FINAL, RunStatus.CANCELLED},
    RunStatus.PARTIALLY_COMPLETED: {RunStatus.RUNNING, RunStatus.COMPLETED, RunStatus.CANCELLED},
    RunStatus.FAILED_RETRYABLE: {RunStatus.RETRYING, RunStatus.FAILED_FINAL, RunStatus.CANCELLED},
    RunStatus.COMPLETED: set(),
    RunStatus.FAILED_FINAL: set(),
    RunStatus.CANCELLED: set(),
}

TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.BACKLOG: {TaskStatus.READY, TaskStatus.CANCELLED},
    TaskStatus.READY: {TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {
        TaskStatus.IN_REVIEW,
        TaskStatus.BLOCKED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.IN_REVIEW: {
        TaskStatus.CHANGES_REQUESTED,
        TaskStatus.IN_TEST,
        TaskStatus.BLOCKED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.CHANGES_REQUESTED: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.IN_TEST: {
        TaskStatus.SECURITY_REVIEW,
        TaskStatus.CHANGES_REQUESTED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.SECURITY_REVIEW: {
        TaskStatus.OPERATIONAL_REVIEW,
        TaskStatus.CHANGES_REQUESTED,
        TaskStatus.BLOCKED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.OPERATIONAL_REVIEW: {
        TaskStatus.READY_FOR_RELEASE,
        TaskStatus.CHANGES_REQUESTED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.READY_FOR_RELEASE: {TaskStatus.DONE, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
    TaskStatus.DONE: set(),
    TaskStatus.BLOCKED: {TaskStatus.READY, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.FAILED: {TaskStatus.READY, TaskStatus.CANCELLED},
    TaskStatus.CANCELLED: set(),
}


class InvalidTransitionError(Exception):
    """Transição de estado inválida (regra 10.4)."""


def validate_transition(current: StrEnum, target: StrEnum, table: dict) -> None:
    allowed = table.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError(
            f"Transição inválida: {current} -> {target}. Permitidas: {sorted(s for s in allowed)}"
        )
