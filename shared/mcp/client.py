"""Cliente MCP mínimo (JSON-RPC 2.0) com transportes stdio e HTTP.

Escopo desta fase: handshake (`initialize` + `notifications/initialized`) e
descoberta de ferramentas (`tools/list`). `call_tool` já está implementado para
ser reaproveitado pelo runtime dos agentes na fase 2, mas ainda não é chamado
em nenhum fluxo de execução.

Transportes:
- "stdio": sobe o servidor como subprocesso e troca mensagens JSON delimitadas
  por linha (transporte padrão do MCP para servidores locais, ex.: uvx).
- "http": POST JSON-RPC no endpoint (MCP Streamable HTTP). Aceita resposta
  application/json ou text/event-stream.

ATENÇÃO (segurança): um servidor stdio é um comando arbitrário executado no
container. Quem configura um servidor MCP consegue, por definição, executar
código nesse container — por isso a API restringe a criação/edição ao papel
mais alto e servidores nascem desabilitados.
"""
import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from shared.logging import get_logger
from shared.mcp.oauth import parse_www_authenticate

logger = get_logger("shared.mcp")

# Versão do protocolo amplamente suportada pelos servidores atuais.
PROTOCOL_VERSION = "2024-11-05"
CLIENT_INFO = {"name": "software-factory", "version": "1.0.0"}
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_LINE_BYTES = 8 * 1024 * 1024


class MCPConnectionError(Exception):
    """Falha ao conectar, fazer handshake ou conversar com o servidor MCP."""


class MCPAuthorizationRequired(MCPConnectionError):
    """O servidor exigiu autorização OAuth (HTTP 401).

    Carrega a URL de Protected Resource Metadata anunciada no header
    WWW-Authenticate, quando presente, para iniciar a descoberta OAuth sem
    precisar adivinhar endpoints (ver shared/mcp/oauth.py).
    """

    def __init__(self, message: str, resource_metadata_url: str | None = None) -> None:
        super().__init__(message)
        self.resource_metadata_url = resource_metadata_url


@dataclass
class MCPServerConfig:
    name: str
    transport: str = "stdio"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    # Access token OAuth (transporte http). Enviado como Bearer; quando ausente
    # e o servidor exigir autorização, o cliente levanta
    # MCPAuthorizationRequired para a UI oferecer o fluxo de autorização.
    access_token: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "MCPServerConfig":
        return cls(
            name=data.get("name") or "",
            transport=(data.get("transport") or "stdio").lower(),
            command=data.get("command"),
            args=list(data.get("args") or []),
            env=dict(data.get("env") or {}),
            url=data.get("url"),
            headers=dict(data.get("headers") or {}),
            timeout_seconds=float(data.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS),
            access_token=data.get("access_token"),
        )

    def validate(self) -> None:
        if self.transport not in ("stdio", "http"):
            raise MCPConnectionError(f"Transporte não suportado: {self.transport}")
        if self.transport == "stdio" and not (self.command or "").strip():
            raise MCPConnectionError("Transporte stdio exige 'command'")
        if self.transport == "http" and not (self.url or "").strip():
            raise MCPConnectionError("Transporte http exige 'url'")


def _initialize_params() -> dict:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": CLIENT_INFO,
    }


def _request(request_id: int, method: str, params: dict | None = None) -> dict:
    message: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return message


def _notification(method: str, params: dict | None = None) -> dict:
    message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        message["params"] = params
    return message


def _raise_for_rpc_error(payload: dict) -> dict:
    if "error" in payload:
        error = payload["error"] or {}
        raise MCPConnectionError(
            f"Erro do servidor MCP ({error.get('code', '?')}): {error.get('message', 'sem mensagem')}"
        )
    return payload.get("result") or {}


def normalize_tools(result: dict) -> list[dict]:
    """Extrai a lista de ferramentas de um resultado de `tools/list`."""
    tools = []
    for tool in result.get("tools") or []:
        if not isinstance(tool, dict) or not tool.get("name"):
            continue
        tools.append(
            {
                "name": tool["name"],
                "description": (tool.get("description") or "").strip(),
                "input_schema": tool.get("inputSchema") or tool.get("input_schema") or {},
            }
        )
    return sorted(tools, key=lambda t: t["name"])


# --------------------------- transporte stdio ---------------------------


class _StdioSession:
    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self.process: asyncio.subprocess.Process | None = None
        self._next_id = 0

    async def __aenter__(self) -> "_StdioSession":
        # Ambiente mínimo + variáveis declaradas: evita repassar todo o
        # ambiente do container (que contém credenciais de banco, MinIO etc.)
        # para um processo de terceiros.
        env = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", "/tmp"),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
        }
        env.update(self.config.env)
        try:
            self.process = await asyncio.create_subprocess_exec(
                self.config.command,
                *self.config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                limit=MAX_LINE_BYTES,
            )
        except FileNotFoundError as exc:
            raise MCPConnectionError(
                f"Comando não encontrado no container: {self.config.command}"
            ) from exc
        except OSError as exc:
            raise MCPConnectionError(f"Falha ao iniciar o servidor MCP: {exc}") from exc
        return self

    async def __aexit__(self, *exc_info) -> None:
        process = self.process
        if process is None:
            return
        try:
            if process.stdin is not None and not process.stdin.is_closing():
                process.stdin.close()
        except Exception:  # noqa: BLE001
            pass
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()

    async def _stderr_tail(self) -> str:
        process = self.process
        if process is None or process.stderr is None:
            return ""
        try:
            data = await asyncio.wait_for(process.stderr.read(4096), timeout=1)
        except (asyncio.TimeoutError, Exception):  # noqa: BLE001
            return ""
        return (data or b"").decode("utf-8", "replace").strip()[:500]

    async def _send(self, message: dict) -> None:
        process = self.process
        if process is None or process.stdin is None:
            raise MCPConnectionError("Servidor MCP não está em execução")
        payload = (json.dumps(message, ensure_ascii=False) + "\n").encode()
        process.stdin.write(payload)
        await process.stdin.drain()

    async def _read_response(self, request_id: int) -> dict:
        """Lê linhas até encontrar a resposta do id pedido (ignora notificações)."""
        process = self.process
        if process is None or process.stdout is None:
            raise MCPConnectionError("Servidor MCP não está em execução")
        deadline = asyncio.get_event_loop().time() + self.config.timeout_seconds
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise MCPConnectionError(
                    f"Timeout de {self.config.timeout_seconds:g}s aguardando resposta do servidor"
                )
            try:
                line = await asyncio.wait_for(process.stdout.readline(), timeout=remaining)
            except asyncio.TimeoutError as exc:
                raise MCPConnectionError(
                    f"Timeout de {self.config.timeout_seconds:g}s aguardando resposta do servidor"
                ) from exc
            if not line:
                stderr = await self._stderr_tail()
                detail = f" stderr: {stderr}" if stderr else ""
                raise MCPConnectionError(f"Servidor MCP encerrou sem responder.{detail}")
            text = line.decode("utf-8", "replace").strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                # Servidores costumam escrever logs em stdout; ignora ruído.
                logger.debug(f"mcp_non_json_stdout line={text[:200]}")
                continue
            if payload.get("id") == request_id:
                return payload

    async def request(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        request_id = self._next_id
        await self._send(_request(request_id, method, params))
        return _raise_for_rpc_error(await self._read_response(request_id))

    async def notify(self, method: str, params: dict | None = None) -> None:
        await self._send(_notification(method, params))

    async def handshake(self) -> dict:
        result = await self.request("initialize", _initialize_params())
        await self.notify("notifications/initialized")
        return result


# ---------------------------- transporte http ----------------------------


class _HttpSession:
    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self._next_id = 0
        self._session_id: str | None = None
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "_HttpSession":
        self._client = httpx.AsyncClient(timeout=self.config.timeout_seconds)
        return self

    async def __aexit__(self, *exc_info) -> None:
        if self._client is not None:
            await self._client.aclose()

    def _request_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        # Token OAuth primeiro para que um header Authorization configurado
        # manualmente ainda possa sobrescrevê-lo (casos de token estático).
        if self.config.access_token:
            headers["Authorization"] = f"Bearer {self.config.access_token}"
        headers.update(self.config.headers)
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    @staticmethod
    def _parse_sse(text: str) -> dict:
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data = line[len("data:") :].strip()
            if not data:
                continue
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                continue
        raise MCPConnectionError("Resposta SSE do servidor MCP sem payload JSON válido")

    async def _post(self, message: dict) -> httpx.Response:
        assert self._client is not None
        try:
            response = await self._client.post(
                self.config.url, json=message, headers=self._request_headers()
            )
        except httpx.HTTPError as exc:
            raise MCPConnectionError(f"Falha de rede ao chamar o servidor MCP: {exc}") from exc
        if response.status_code in (401, 403):
            # 401/403 aqui significa "precisa autorizar" (ou token expirado):
            # o header WWW-Authenticate aponta a Protected Resource Metadata,
            # ponto de partida do fluxo OAuth (RFC 9728).
            params = parse_www_authenticate(response.headers.get("www-authenticate"))
            raise MCPAuthorizationRequired(
                f"O servidor MCP exige autorização (HTTP {response.status_code}): "
                f"{response.text[:200]}",
                resource_metadata_url=params.get("resource_metadata"),
            )
        if response.status_code >= 400:
            raise MCPConnectionError(
                f"Servidor MCP respondeu HTTP {response.status_code}: {response.text[:200]}"
            )
        session_id = response.headers.get("mcp-session-id")
        if session_id:
            self._session_id = session_id
        return response

    async def request(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        response = await self._post(_request(self._next_id, method, params))
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            payload = self._parse_sse(response.text)
        else:
            try:
                payload = response.json()
            except ValueError as exc:
                raise MCPConnectionError(
                    f"Resposta do servidor MCP não é JSON: {response.text[:200]}"
                ) from exc
        return _raise_for_rpc_error(payload)

    async def notify(self, method: str, params: dict | None = None) -> None:
        await self._post(_notification(method, params))

    async def handshake(self) -> dict:
        result = await self.request("initialize", _initialize_params())
        await self.notify("notifications/initialized")
        return result


def _session(config: MCPServerConfig):
    config.validate()
    return _StdioSession(config) if config.transport == "stdio" else _HttpSession(config)


# ------------------------------- operações -------------------------------


async def discover_tools(config: MCPServerConfig) -> dict:
    """Conecta, faz handshake e lista as ferramentas expostas pelo servidor."""
    async with _session(config) as session:
        info = await session.handshake()
        tools = normalize_tools(await session.request("tools/list"))
    server_info = info.get("serverInfo") or {}
    return {
        "server_name": server_info.get("name") or config.name,
        "server_version": server_info.get("version") or "",
        "protocol_version": info.get("protocolVersion") or PROTOCOL_VERSION,
        "capabilities": info.get("capabilities") or {},
        "tools": tools,
    }


async def call_tool(config: MCPServerConfig, tool_name: str, arguments: dict) -> dict:
    """Executa uma ferramenta MCP. Preparado para a fase 2 (tool calling)."""
    async with _session(config) as session:
        await session.handshake()
        return await session.request(
            "tools/call", {"name": tool_name, "arguments": arguments or {}}
        )
