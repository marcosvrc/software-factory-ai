"""Testes de segurança (seção 26.6): proibições do sandbox e path traversal."""
import pytest

from sandbox.runner.runner import validate_sandbox_config
from shared.exceptions import SandboxViolationError


def _valid(**overrides):
    params = dict(
        image="factory-sandbox-python:latest",
        workspace="/workspaces/proj-1",
        privileged=False,
        user="1000:1000",
        network_mode="none",
    )
    params.update(overrides)
    return params


def test_valid_config_passes():
    validate_sandbox_config(**_valid())


def test_privileged_forbidden():
    with pytest.raises(SandboxViolationError):
        validate_sandbox_config(**_valid(privileged=True))


def test_root_mount_forbidden():
    with pytest.raises(SandboxViolationError):
        validate_sandbox_config(**_valid(workspace="/"))


def test_root_user_forbidden():
    with pytest.raises(SandboxViolationError):
        validate_sandbox_config(**_valid(user="root"))


def test_network_forbidden():
    with pytest.raises(SandboxViolationError):
        validate_sandbox_config(**_valid(network_mode="bridge"))


def test_unapproved_image_forbidden():
    with pytest.raises(SandboxViolationError):
        validate_sandbox_config(**_valid(image="alpine:latest"))
