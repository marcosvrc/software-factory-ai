"""Scanners de segurança: security.run_sast / scan_dependencies / scan_secrets /
scan_container (Épico 7). Executados no sandbox; gates decididos pelo policy gate."""
from typing import Any

from sandbox.runner.runner import run_in_sandbox


def _scanner(tool_name: str, command: list[str]):
    class _Tool:
        name = tool_name

        async def execute(self, *, execution_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
            return await run_in_sandbox(
                workspace=arguments["workspace"],
                command=command,
                timeout_seconds=int(arguments.get("timeout_seconds", 600)),
            )

    return _Tool()


SecurityRunSast = _scanner("security.run_sast", ["bandit", "-r", ".", "-f", "json"])
SecurityScanDependencies = _scanner(
    "security.scan_dependencies", ["pip-audit", "--format", "json"]
)
SecurityScanSecrets = _scanner(
    "security.scan_secrets", ["gitleaks", "detect", "--source", ".", "--report-format", "json"]
)
SecurityScanContainer = _scanner(
    "security.scan_container", ["trivy", "fs", "--format", "json", "."]
)
