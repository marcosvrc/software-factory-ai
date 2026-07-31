"""Testes das máquinas de estado (seções 10 e 26.1)."""
import pytest

from shared.contracts.states import (
    PROJECT_TRANSITIONS,
    RUN_TRANSITIONS,
    TASK_TRANSITIONS,
    InvalidTransitionError,
    ProjectStatus,
    RunStatus,
    TaskStatus,
    validate_transition,
)


def test_project_valid_transition():
    validate_transition(ProjectStatus.DRAFT, ProjectStatus.PLANNING, PROJECT_TRANSITIONS)


def test_project_invalid_transition():
    with pytest.raises(InvalidTransitionError):
        validate_transition(ProjectStatus.ARCHIVED, ProjectStatus.ACTIVE, PROJECT_TRANSITIONS)


def test_run_completed_is_terminal():
    assert RUN_TRANSITIONS[RunStatus.COMPLETED] == set()


def test_task_done_immutable():
    """Tarefa concluída não pode ser alterada sem nova versão (regra 10.4)."""
    assert TASK_TRANSITIONS[TaskStatus.DONE] == set()


def test_task_flow_happy_path():
    path = [
        TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW,
        TaskStatus.IN_TEST, TaskStatus.SECURITY_REVIEW, TaskStatus.OPERATIONAL_REVIEW,
        TaskStatus.READY_FOR_RELEASE, TaskStatus.DONE,
    ]
    for current, target in zip(path, path[1:]):
        validate_transition(current, target, TASK_TRANSITIONS)
