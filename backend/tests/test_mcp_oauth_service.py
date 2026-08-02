"""Testes do serviço de OAuth dos servidores MCP (app/services/mcp_oauth.py)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.services import mcp_oauth
from shared.mcp.oauth import MCPOAuthError


class _Server:
    def __init__(self, **kw):
        self.name = kw.get("name", "notion")
        self.transport = kw.get("transport", "http")
        self.url = kw.get("url", "https://mcp.notion.com/mcp")
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
        self.last_status = kw.get("last_status")


ASM = {
    "authorization_endpoint": "https://auth.notion.com/authorize",
    "token_endpoint": "https://auth.notion.com/token",
    "registration_endpoint": "https://auth.notion.com/register",
}
METADATA = {"authorization_server": ASM, "protected_resource": {"resource": "https://r"}}


def test_authorization_status_not_applicable_for_stdio():
    assert mcp_oauth.authorization_status(_Server(transport="stdio")) == "not_applicable"


def test_authorization_status_not_authorized_without_token():
    assert mcp_oauth.authorization_status(_Server()) == "not_authorized"


def test_authorization_status_authorized_with_valid_token():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    server = _Server(oauth_access_token="at", oauth_expires_at=future)
    assert mcp_oauth.authorization_status(server) == "authorized"


def test_authorization_status_expired_without_refresh_token():
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    server = _Server(oauth_access_token="at", oauth_expires_at=past)
    assert mcp_oauth.authorization_status(server) == "expired"


def test_authorization_status_authorized_when_refresh_available():
    """Expirado mas com refresh_token é renovável, então segue 'authorized'."""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    server = _Server(oauth_access_token="at", oauth_expires_at=past, oauth_refresh_token="rt")
    assert mcp_oauth.authorization_status(server) == "authorized"


def test_clear_authorization_removes_tokens_and_pending_state():
    server = _Server(
        oauth_access_token="at",
        oauth_refresh_token="rt",
        oauth_expires_at=datetime.now(timezone.utc),
        oauth_state="st",
        oauth_code_verifier="cv",
    )
    mcp_oauth.clear_authorization(server)
    assert server.oauth_access_token is None
    assert server.oauth_refresh_token is None
    assert server.oauth_expires_at is None
    assert server.oauth_state is None
    assert server.oauth_code_verifier is None


def test_clear_authorization_keeps_registered_client():
    """O client_id vem de registro dinâmico; revogar tokens não deve exigir
    registrar o cliente de novo."""
    server = _Server(oauth_access_token="at", oauth_client_id="cli", oauth_client_secret="sec")
    mcp_oauth.clear_authorization(server)
    assert server.oauth_client_id == "cli"
    assert server.oauth_client_secret == "sec"


async def test_prepare_authorization_rejects_stdio():
    with pytest.raises(MCPOAuthError):
        await mcp_oauth.prepare_authorization(_Server(transport="stdio"))


async def test_prepare_authorization_rejects_server_without_url():
    with pytest.raises(MCPOAuthError):
        await mcp_oauth.prepare_authorization(_Server(url=None))


async def test_prepare_authorization_registers_client_and_stores_pkce(monkeypatch):
    server = _Server(oauth_metadata=METADATA)

    async def fake_register(endpoint, redirect, scope=""):
        assert endpoint == ASM["registration_endpoint"]
        return {"client_id": "cli-novo", "client_secret": "sec"}

    monkeypatch.setattr(mcp_oauth.oauth, "register_client", fake_register)

    url = await mcp_oauth.prepare_authorization(server)

    assert server.oauth_client_id == "cli-novo"
    assert server.oauth_client_secret == "sec"
    assert server.oauth_state and server.oauth_code_verifier
    assert server.oauth_state in url
    assert "code_challenge=" in url
    assert ASM["authorization_endpoint"] in url


async def test_prepare_authorization_reuses_existing_client(monkeypatch):
    server = _Server(oauth_metadata=METADATA, oauth_client_id="cli-existente")

    async def fail_register(*a, **k):
        raise AssertionError("não deveria registrar cliente novamente")

    monkeypatch.setattr(mcp_oauth.oauth, "register_client", fail_register)
    url = await mcp_oauth.prepare_authorization(server)
    assert "cli-existente" in url


async def test_prepare_authorization_without_registration_support_raises(monkeypatch):
    asm = {k: v for k, v in ASM.items() if k != "registration_endpoint"}
    server = _Server(oauth_metadata={"authorization_server": asm, "protected_resource": {}})
    with pytest.raises(MCPOAuthError) as exc:
        await mcp_oauth.prepare_authorization(server)
    assert "registro dinâmico" in str(exc.value)


async def test_prepare_authorization_discovers_metadata_when_absent(monkeypatch):
    server = _Server()
    calls = {}

    async def fake_prm(url, hint_url=None):
        calls["prm"] = (url, hint_url)
        return {"authorization_servers": ["https://auth.notion.com"], "resource": "https://res"}

    async def fake_asm(issuer):
        calls["asm"] = issuer
        return ASM

    async def fake_register(endpoint, redirect, scope=""):
        return {"client_id": "cli"}

    monkeypatch.setattr(mcp_oauth.oauth, "fetch_protected_resource_metadata", fake_prm)
    monkeypatch.setattr(mcp_oauth.oauth, "fetch_authorization_server_metadata", fake_asm)
    monkeypatch.setattr(mcp_oauth.oauth, "register_client", fake_register)

    await mcp_oauth.prepare_authorization(server, resource_metadata_url="https://hint")

    assert calls["prm"] == ("https://mcp.notion.com/mcp", "https://hint")
    assert calls["asm"] == "https://auth.notion.com"
    assert server.oauth_resource == "https://res"
    assert server.oauth_metadata["authorization_server"] == ASM


async def test_complete_authorization_stores_tokens(monkeypatch):
    server = _Server(
        oauth_metadata=METADATA,
        oauth_client_id="cli",
        oauth_code_verifier="cv",
        oauth_state="st",
    )
    expires = datetime.now(timezone.utc) + timedelta(hours=1)

    async def fake_exchange(**kwargs):
        assert kwargs["code"] == "código"
        assert kwargs["code_verifier"] == "cv"
        return {"access_token": "at", "refresh_token": "rt", "expires_at": expires, "scope": "read"}

    monkeypatch.setattr(mcp_oauth.oauth, "exchange_code", fake_exchange)
    await mcp_oauth.complete_authorization(server, "código")

    assert server.oauth_access_token == "at"
    assert server.oauth_refresh_token == "rt"
    assert server.oauth_expires_at == expires
    # estado da autorização em andamento é limpo para não permitir reuso
    assert server.oauth_state is None
    assert server.oauth_code_verifier is None


async def test_complete_authorization_without_pending_flow_raises():
    server = _Server(oauth_metadata=METADATA, oauth_client_id="cli")
    with pytest.raises(MCPOAuthError):
        await mcp_oauth.complete_authorization(server, "código")


async def test_complete_authorization_without_metadata_raises():
    server = _Server(oauth_code_verifier="cv", oauth_client_id="cli")
    with pytest.raises(MCPOAuthError):
        await mcp_oauth.complete_authorization(server, "código")


async def test_ensure_fresh_token_returns_none_without_authorization():
    assert await mcp_oauth.ensure_fresh_token(_Server()) is None


async def test_ensure_fresh_token_keeps_valid_token(monkeypatch):
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    server = _Server(oauth_access_token="at", oauth_expires_at=future)

    async def fail_refresh(**k):
        raise AssertionError("não deveria renovar token válido")

    monkeypatch.setattr(mcp_oauth.oauth, "refresh_access_token", fail_refresh)
    assert await mcp_oauth.ensure_fresh_token(server) == "at"


async def test_ensure_fresh_token_refreshes_expired_token(monkeypatch):
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    server = _Server(
        oauth_metadata=METADATA,
        oauth_client_id="cli",
        oauth_access_token="antigo",
        oauth_refresh_token="rt",
        oauth_expires_at=past,
    )

    async def fake_refresh(**kwargs):
        assert kwargs["refresh_token"] == "rt"
        return {
            "access_token": "novo",
            "refresh_token": "rt2",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "scope": "",
        }

    monkeypatch.setattr(mcp_oauth.oauth, "refresh_access_token", fake_refresh)
    assert await mcp_oauth.ensure_fresh_token(server) == "novo"
    assert server.oauth_refresh_token == "rt2"


async def test_failed_refresh_clears_authorization(monkeypatch):
    """Refresh inválido deve exigir nova autorização, em vez de insistir com um
    token que nunca vai funcionar."""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    server = _Server(
        oauth_metadata=METADATA,
        oauth_client_id="cli",
        oauth_access_token="antigo",
        oauth_refresh_token="rt",
        oauth_expires_at=past,
    )

    async def fake_refresh(**kwargs):
        raise MCPOAuthError("invalid_grant")

    monkeypatch.setattr(mcp_oauth.oauth, "refresh_access_token", fake_refresh)
    assert await mcp_oauth.ensure_fresh_token(server) is None
    assert server.oauth_access_token is None


def test_redirect_uri_is_configurable(monkeypatch):
    monkeypatch.setenv("MCP_OAUTH_REDIRECT_URI", "https://fabrica.local/cb")
    assert mcp_oauth.redirect_uri() == "https://fabrica.local/cb"


def test_redirect_uri_default(monkeypatch):
    monkeypatch.delenv("MCP_OAUTH_REDIRECT_URI", raising=False)
    assert mcp_oauth.redirect_uri().endswith("/api/v1/mcp/oauth/callback")
