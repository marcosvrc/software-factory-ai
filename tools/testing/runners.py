"""Runners de teste e qualidade: test.run_* e quality.run_* (Épico 6).

Todos executam DENTRO do sandbox efêmero (seção 16.1: código gerado nunca é
executado diretamente no container do orquestrador/worker).
"""
from typing import Any

from sandbox.runner.runner import run_in_sandbox


def _runner(tool_name: str, command: list[str]):
    class _Tool:
        name = tool_name

        async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
            return await run_in_sandbox(
                workspace=arguments["workspace"],
                command=command,
                timeout_seconds=int(arguments.get("timeout_seconds", 300)),
            )

    return _Tool()


TestRunUnit = _runner("test.run_unit", ["pytest", "-q", "--maxfail", "5"])
TestRunIntegration = _runner("test.run_integration", ["pytest", "-q", "-m", "integration"])
TestRunE2E = _runner("test.run_e2e", ["pytest", "-q", "-m", "e2e"])
QualityRunLint = _runner("quality.run_lint", ["ruff", "check", "."])
QualityRunTypeCheck = _runner("quality.run_type_check", ["mypy", "."])
QualityRunComplexity = _runner("quality.run_complexity", ["python", "-m", "radon", "cc", "-s", "."])
