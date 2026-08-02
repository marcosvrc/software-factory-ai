"""Testes dos helpers da API de servidores MCP.

Foco no que é fácil de errar e tem consequência: não vazar valores de env/
headers (podem conter tokens) e validar os campos exigidos por transporte.
"""
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.api.v1.mcp import _to_config, _to_out, _validate_transport_fields


class _Server:
    def __init__(self, **kw):
        now = datetime.now(timezone.utc)
        self.id = kw.get("id", "srv-1")
        self.name = kw.get("name", "github")
        self.description = kw.get("description", "Servidor MCP do GitHub")
        self.transport = kw.get("transport", "stdio")
        self.command = kw.get("command", "uvx")
        self.args = kw.get("args", ["mcp-server-git"])
        self.env = kw.get("env", {"GITHUB_TOKEN": "ghp_supersecreto", "LOG_LEVEL": "ERROR"})
        self.url = kw.get("url")
        self.headers = kw.get("headers", {"Authorization": "Bearer segredo"})
        self.timeout_seconds = kw.get("timeout_seconds", 30)
        self.enabled = kw.get("enabled", False)
        self.tools = kw.get("tools", [{"name": "git_log", "description": "", "input_schema": {}}])
        self.last_status = kw.get("last_status", "OK")
        self.last_error = kw.get("last_error")
        self.last_checked_at = kw.get("last_checked_at", now)
        self.created_at = now
        self.updated_at = now
        # OAuth (usado por _to_out via authorization_status)
        self.oauth_metadata = kw.get("oauth_metadata", {})
        self.oauth_client_id = kw.get("oauth_client_id")
        self.oauth_client_secret = kw.get("oauth_client_secret")
        self.oauth_scope = kw.get("oauth_scope")
        self.oauth_resource = kw.get("oauth_resource")
        self.oauth_access_token = kw.get("oauth_access_token")
        self.oauth_refresh_token = kw.get("oauth_refresh_token")
        self.oauth_expires_at = kw.get("oauth_expires_at")
        self.oauth_state = kw.get("oauth_state")
        self.oauth_code_verifier = kw.get("oauth_code_verifier")


def test_secret_values_are_never_exposed():
    out = _to_out(_Server())
    serialized = out.model_dump_json()
    assert "ghp_supersecreto" not in serialized
    assert "Bearer segredo" not in serialized


def test_oauth_tokens_are_never_exposed():
    """Tokens OAuth e client_secret são segredos: a API só expõe o estado."""
    out = _to_out(
        _Server(
            transport="http",
            url="https://mcp.notion.com/mcp",
            command=None,
            oauth_access_token="at_muito_secreto",
            oauth_refresh_token="rt_muito_secreto",
            oauth_client_id="cli-publico",
            oauth_client_secret="cs_muito_secreto",
            oauth_code_verifier="cv_secreto",
        )
    )
    serialized = out.model_dump_json()
    for secret in ("at_muito_secreto", "rt_muito_secreto", "cs_muito_secreto", "cv_secreto"):
        assert secret not in serialized
    assert out.has_oauth_client is True
    assert out.auth_status == "authorized"


def test_auth_status_reflects_missing_authorization():
    out = _to_out(_Server(transport="http", url="https://mcp.notion.com/mcp", command=None))
    assert out.auth_status == "not_authorized"


def test_auth_status_not_applicable_for_stdio():
    assert _to_out(_Server()).auth_status == "not_applicable"


def test_secret_keys_are_exposed_for_reference():
    out = _to_out(_Server())
    assert out.env_keys == ["GITHUB_TOKEN", "LOG_LEVEL"]
    assert out.header_keys == ["Authorization"]


def test_tools_and_status_are_exposed():
    out = _to_out(_Server())
    assert [t["name"] for t in out.tools] == ["git_log"]
    assert out.last_status == "OK"


def test_used_by_agents_is_included():
    out = _to_out(_Server(), used_by=["engineering.backend"])
    assert out.used_by_agents == ["engineering.backend"]


def test_to_config_carries_secrets_for_connection():
    """A conexão precisa dos valores reais (só a resposta da API é redigida)."""
    config = _to_config(_Server())
    assert config.env["GITHUB_TOKEN"] == "ghp_supersecreto"
    assert config.headers["Authorization"] == "Bearer segredo"
    assert config.timeout_seconds == 30.0


def test_stdio_requires_command():
    with pytest.raises(HTTPException) as exc:
        _validate_transport_fields("stdio", None, None)
    assert exc.value.status_code == 422


def test_stdio_rejects_blank_command():
    with pytest.raises(HTTPException):
        _validate_transport_fields("stdio", "   ", None)


def test_http_requires_url():
    with pytest.raises(HTTPException) as exc:
        _validate_transport_fields("http", None, None)
    assert exc.value.status_code == 422


def test_valid_transports_pass():
    _validate_transport_fields("stdio", "uvx", None)
    _validate_transport_fields("http", None, "https://exemplo/mcp")
