"""Testes de materialização de code_files no workspace do projeto em disco
(workers/base/artifacts.write_code_file_to_workspace).

Cobre principalmente a proteção contra path traversal: `path` vem do modelo
de IA e não é confiável (ver agents/prompts/base.txt regra 9).
"""
import importlib
import sys

import pytest

from shared.exceptions import SandboxViolationError


@pytest.fixture()
def artifacts_module(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACES_ROOT", str(tmp_path))
    # Recarrega o módulo para que WORKSPACES_ROOT seja lido com o novo valor
    # (a constante é resolvida no import, não a cada chamada).
    sys.modules.pop("workers.base.artifacts", None)
    module = importlib.import_module("workers.base.artifacts")
    yield module
    sys.modules.pop("workers.base.artifacts", None)


def test_writes_file_inside_project_workspace(artifacts_module, tmp_path):
    result = artifacts_module.write_code_file_to_workspace(
        project_id="proj-1", path="src/api.py", content="print(1)"
    )
    assert result is not None
    written = tmp_path / "proj-1" / "src" / "api.py"
    assert written.read_text() == "print(1)"


def test_creates_nested_directories(artifacts_module, tmp_path):
    artifacts_module.write_code_file_to_workspace(
        project_id="proj-1", path="a/b/c/deep.py", content="x = 1"
    )
    assert (tmp_path / "proj-1" / "a" / "b" / "c" / "deep.py").exists()


def test_blocks_path_traversal_with_dotdot(artifacts_module):
    with pytest.raises(SandboxViolationError):
        artifacts_module.write_code_file_to_workspace(
            project_id="proj-1", path="../../etc/passwd", content="malicious"
        )


def test_absolute_path_is_treated_as_relative_to_workspace(artifacts_module, tmp_path):
    """Um path absoluto vindo do modelo (ex.: "/etc/passwd") é normalizado
    para relativo dentro do workspace, em vez de escapar para o filesystem
    do host — comportamento seguro por construção (lstrip("/"))."""
    artifacts_module.write_code_file_to_workspace(
        project_id="proj-1", path="/etc/passwd", content="not actually /etc/passwd"
    )
    written = tmp_path / "proj-1" / "etc" / "passwd"
    assert written.read_text() == "not actually /etc/passwd"


def test_returns_none_without_project_id(artifacts_module):
    assert (
        artifacts_module.write_code_file_to_workspace(
            project_id="", path="a.py", content="x"
        )
        is None
    )


def test_different_projects_are_isolated(artifacts_module, tmp_path):
    artifacts_module.write_code_file_to_workspace(
        project_id="proj-1", path="a.py", content="one"
    )
    artifacts_module.write_code_file_to_workspace(
        project_id="proj-2", path="a.py", content="two"
    )
    assert (tmp_path / "proj-1" / "a.py").read_text() == "one"
    assert (tmp_path / "proj-2" / "a.py").read_text() == "two"
