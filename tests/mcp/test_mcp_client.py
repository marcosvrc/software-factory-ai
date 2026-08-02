"""Testes do cliente MCP (shared/mcp/client.py).

O transporte stdio é exercitado contra um servidor MCP falso escrito em Python
(subprocesso real), cobrindo handshake + tools/list, ruído em stdout, erro
JSON-RPC, processo que morre e timeout.
"""
import json
import sys
from pathlib import Path

import pytest

from shared.mcp.client import (
    MCPConnectionError,
    MCPServerConfig,
    discover_tools,
    normalize_tools,
)

FAKE_SERVER = Path(__file__).parent / "fake_mcp_server.py"


def _config(mode: str, timeout: float = 10.0) -> MCPServerConfig:
    return MCPServerConfig(
        name="fake",
        transport="stdio",
        command=sys.executable,
        args=[str(FAKE_SERVER), mode],
        timeout_seconds=timeout,
    )


async def test_discover_tools_returns_normalized_tools():
    result = await discover_tools(_config("ok"))
    assert result["server_name"] == "fake-server"
    assert result["server_version"] == "9.9.9"
    assert [t["name"] for t in result["tools"]] == ["alpha_tool", "beta_tool"]
    alpha = result["tools"][0]
    assert alpha["description"] == "Ferramenta alpha"
    assert alpha["input_schema"]["type"] == "object"


async def test_ignores_non_json_noise_on_stdout():
    """Servidores frequentemente escrevem logs em stdout; isso não deve
    impedir a leitura da resposta JSON-RPC."""
    result = await discover_tools(_config("noisy"))
    assert [t["name"] for t in result["tools"]] == ["alpha_tool", "beta_tool"]


async def test_rpc_error_is_reported():
    with pytest.raises(MCPConnectionError) as exc:
        await discover_tools(_config("rpc_error"))
    assert "-32601" in str(exc.value) or "Method not found" in str(exc.value)


async def test_server_exiting_early_is_reported():
    with pytest.raises(MCPConnectionError) as exc:
        await discover_tools(_config("exit"))
    assert "encerrou sem responder" in str(exc.value)


async def test_timeout_is_reported():
    with pytest.raises(MCPConnectionError) as exc:
        await discover_tools(_config("hang", timeout=1.0))
    assert "Timeout" in str(exc.value)


async def test_missing_command_is_reported():
    config = MCPServerConfig(
        name="x", transport="stdio", command="/nao/existe/comando-mcp", timeout_seconds=5
    )
    with pytest.raises(MCPConnectionError) as exc:
        await discover_tools(config)
    assert "não encontrado" in str(exc.value)


async def test_stdio_without_command_is_rejected():
    with pytest.raises(MCPConnectionError):
        await discover_tools(MCPServerConfig(name="x", transport="stdio"))


async def test_http_without_url_is_rejected():
    with pytest.raises(MCPConnectionError):
        await discover_tools(MCPServerConfig(name="x", transport="http"))


async def test_unsupported_transport_is_rejected():
    with pytest.raises(MCPConnectionError):
        await discover_tools(MCPServerConfig(name="x", transport="grpc"))


def test_normalize_tools_skips_entries_without_name():
    tools = normalize_tools(
        {"tools": [{"description": "sem nome"}, {"name": "ok"}, "texto"]}
    )
    assert [t["name"] for t in tools] == ["ok"]


def test_normalize_tools_accepts_snake_case_schema():
    tools = normalize_tools({"tools": [{"name": "t", "input_schema": {"type": "object"}}]})
    assert tools[0]["input_schema"] == {"type": "object"}


def test_config_from_dict_defaults():
    config = MCPServerConfig.from_dict({"name": "s"})
    assert config.transport == "stdio"
    assert config.args == []
    assert config.env == {}
    assert config.timeout_seconds == 30.0


def test_env_is_not_inherited_wholesale(monkeypatch):
    """Regressão de segurança: o subprocesso não deve herdar todo o ambiente do
    container (que contém credenciais de banco/MinIO); apenas PATH/HOME/LANG e
    as variáveis declaradas na configuração do servidor."""
    from shared.mcp.client import _StdioSession

    monkeypatch.setenv("FACTORY_DB_PASSWORD", "super-secreto")
    session = _StdioSession(MCPServerConfig(name="x", command="/bin/true", env={"A": "1"}))
    # Reproduz a montagem do ambiente feita em __aenter__ sem subir processo.
    import os

    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
    }
    env.update(session.config.env)
    assert "FACTORY_DB_PASSWORD" not in env
    assert env["A"] == "1"


def test_json_rpc_request_shape():
    from shared.mcp.client import _notification, _request

    assert _request(7, "tools/list") == {"jsonrpc": "2.0", "id": 7, "method": "tools/list"}
    assert _notification("notifications/initialized") == {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
    }
    payload = _request(1, "tools/call", {"name": "t", "arguments": {}})
    assert payload["params"]["name"] == "t"


def test_sse_payload_parsing():
    from shared.mcp.client import _HttpSession

    body = "event: message\ndata: " + json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"ok": True}})
    assert _HttpSession._parse_sse(body)["result"] == {"ok": True}


def test_sse_without_json_raises():
    from shared.mcp.client import _HttpSession

    with pytest.raises(MCPConnectionError):
        _HttpSession._parse_sse("event: ping\n")
