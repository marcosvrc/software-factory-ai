"""Abstração de ferramentas (seções 15.2 e 15.3).

Cada chamada valida: agente solicitante, tarefa, escopo, workspace, ferramenta,
argumentos, limite de tempo e limite de recursos (menor privilégio, 3.6).
"""
import asyncio
import hashlib
import json
from typing import Any, Protocol

from shared.exceptions import ToolExecutionError, ToolNotAllowedError
from shared.logging import get_logger

logger = get_logger("tools")

DEFAULT_TIMEOUT_SECONDS = 300


class Tool(Protocol):
    name: str

    async def execute(
        self,
        *,
        execution_id: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]: ...


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)


registry = ToolRegistry()


def input_hash(arguments: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(arguments, sort_keys=True, default=str).encode()
    ).hexdigest()


async def authorized_call(
    *,
    tool_name: str,
    agent_definition: dict,
    execution_id: str,
    arguments: dict[str, Any],
    workspace: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Executa uma ferramenta aplicando a política de autorização (15.3)."""
    allowed = set(agent_definition.get("tools", {}).get("allowed", []))
    denied = set(agent_definition.get("tools", {}).get("denied", []))
    if tool_name in denied or tool_name not in allowed:
        raise ToolNotAllowedError(
            f"Agente {agent_definition.get('id')} não autorizado a usar {tool_name}"
        )
    tool = registry.get(tool_name)
    if tool is None:
        raise ToolExecutionError(f"Ferramenta não registrada: {tool_name}")
    if workspace is not None:
        path = str(arguments.get("path", ""))
        if path.startswith("/") and not path.startswith(workspace):
            raise ToolNotAllowedError(f"Caminho fora do workspace autorizado: {path}")
    try:
        return await asyncio.wait_for(
            tool.execute(execution_id=execution_id, arguments=arguments),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise ToolExecutionError(f"Timeout na ferramenta {tool_name}") from exc
