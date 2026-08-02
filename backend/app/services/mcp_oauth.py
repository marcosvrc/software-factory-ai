"""Orquestração do fluxo OAuth 2.1 dos servidores MCP.

Mantém a lógica de estado (descoberta, registro do cliente, troca e renovação
de tokens) fora do router HTTP, para ser testável e reutilizável.
"""
import os
from datetime import datetime, timezone

from app.models import McpServer
from shared.mcp import oauth
from shared.mcp.oauth import MCPOAuthError

# URI de callback registrada no authorization server. Precisa ser alcançável
# pelo navegador do usuário; por padrão aponta para a própria API exposta em
# localhost. Em outro host/porta, ajuste MCP_OAUTH_REDIRECT_URI.
DEFAULT_REDIRECT_URI = "http://localhost:8000/api/v1/mcp/oauth/callback"


def redirect_uri() -> str:
    return os.getenv("MCP_OAUTH_REDIRECT_URI", DEFAULT_REDIRECT_URI)


def is_authorized(server: McpServer) -> bool:
    return bool(server.oauth_access_token)


def needs_refresh(server: McpServer, *, now: datetime | None = None) -> bool:
    if not server.oauth_access_token:
        return False
    return oauth.is_token_expired(server.oauth_expires_at, now=now) and bool(
        server.oauth_refresh_token
    )


def _store_tokens(server: McpServer, tokens: dict) -> None:
    server.oauth_access_token = tokens["access_token"]
    if tokens.get("refresh_token"):
        server.oauth_refresh_token = tokens["refresh_token"]
    server.oauth_expires_at = tokens.get("expires_at")
    if tokens.get("scope"):
        server.oauth_scope = tokens["scope"]


def clear_authorization(server: McpServer) -> None:
    server.oauth_access_token = None
    server.oauth_refresh_token = None
    server.oauth_expires_at = None
    server.oauth_state = None
    server.oauth_code_verifier = None


async def prepare_authorization(
    server: McpServer, *, resource_metadata_url: str | None = None
) -> str:
    """Descobre a metadata, registra o cliente se preciso e devolve a URL de
    autorização, salvando `state` e `code_verifier` no servidor.

    O caller é responsável por commitar a transação.
    """
    if server.transport != "http":
        raise MCPOAuthError("OAuth se aplica apenas a servidores MCP com transporte http")
    if not server.url:
        raise MCPOAuthError("Servidor sem URL configurada")

    metadata = dict(server.oauth_metadata or {})
    asm = metadata.get("authorization_server") or {}
    prm = metadata.get("protected_resource") or {}

    # Descobre a metadata na primeira autorização (ou quando incompleta).
    if not asm.get("authorization_endpoint") or not asm.get("token_endpoint"):
        prm = await oauth.fetch_protected_resource_metadata(
            server.url, hint_url=resource_metadata_url
        )
        issuer = oauth.select_authorization_server(prm)
        asm = await oauth.fetch_authorization_server_metadata(issuer)
        metadata = {"protected_resource": prm, "authorization_server": asm, "issuer": issuer}

    resource = prm.get("resource") or oauth.canonical_resource(server.url)
    scope = server.oauth_scope or oauth.pick_scope(asm, prm)

    # Registro dinâmico de cliente quando ainda não temos client_id.
    if not server.oauth_client_id:
        registration_endpoint = asm.get("registration_endpoint")
        if not registration_endpoint:
            raise MCPOAuthError(
                "O authorization server não suporta registro dinâmico de cliente e nenhum "
                "client_id foi configurado. Cadastre um client_id manualmente."
            )
        registration = await oauth.register_client(
            registration_endpoint, redirect_uri(), scope=scope
        )
        server.oauth_client_id = registration["client_id"]
        server.oauth_client_secret = registration.get("client_secret")

    verifier, challenge = oauth.generate_pkce()
    state = oauth.generate_state()
    server.oauth_metadata = metadata
    server.oauth_resource = resource
    server.oauth_scope = scope
    server.oauth_state = state
    server.oauth_code_verifier = verifier

    return oauth.build_authorization_url(
        asm=asm,
        client_id=server.oauth_client_id,
        redirect_uri=redirect_uri(),
        state=state,
        code_challenge=challenge,
        resource=resource,
        scope=scope,
    )


async def complete_authorization(server: McpServer, code: str) -> None:
    """Troca o código por tokens e limpa o estado da autorização em andamento."""
    asm = (server.oauth_metadata or {}).get("authorization_server") or {}
    token_endpoint = asm.get("token_endpoint")
    if not token_endpoint:
        raise MCPOAuthError("Metadata sem token_endpoint; refaça a autorização")
    if not server.oauth_code_verifier or not server.oauth_client_id:
        raise MCPOAuthError("Autorização não iniciada corretamente; refaça o fluxo")

    tokens = await oauth.exchange_code(
        token_endpoint=token_endpoint,
        code=code,
        code_verifier=server.oauth_code_verifier,
        client_id=server.oauth_client_id,
        redirect_uri=redirect_uri(),
        resource=server.oauth_resource or oauth.canonical_resource(server.url or ""),
        client_secret=server.oauth_client_secret,
    )
    _store_tokens(server, tokens)
    server.oauth_state = None
    server.oauth_code_verifier = None


async def ensure_fresh_token(server: McpServer) -> str | None:
    """Renova o access_token se estiver expirado. Retorna o token utilizável.

    Falha de renovação limpa a autorização para que a UI peça nova autorização
    em vez de repetir chamadas com um token inválido.
    """
    if not server.oauth_access_token:
        return None
    if not oauth.is_token_expired(server.oauth_expires_at):
        return server.oauth_access_token
    if not server.oauth_refresh_token:
        return server.oauth_access_token

    asm = (server.oauth_metadata or {}).get("authorization_server") or {}
    token_endpoint = asm.get("token_endpoint")
    if not token_endpoint or not server.oauth_client_id:
        return server.oauth_access_token
    try:
        tokens = await oauth.refresh_access_token(
            token_endpoint=token_endpoint,
            refresh_token=server.oauth_refresh_token,
            client_id=server.oauth_client_id,
            resource=server.oauth_resource or oauth.canonical_resource(server.url or ""),
            scope=server.oauth_scope or "",
            client_secret=server.oauth_client_secret,
        )
    except MCPOAuthError:
        clear_authorization(server)
        return None
    _store_tokens(server, tokens)
    return server.oauth_access_token


def authorization_status(server: McpServer) -> str:
    """Status de autorização exibido na UI."""
    if server.transport != "http":
        return "not_applicable"
    if not server.oauth_access_token:
        return "not_authorized"
    if oauth.is_token_expired(server.oauth_expires_at, now=datetime.now(timezone.utc)):
        return "expired" if not server.oauth_refresh_token else "authorized"
    return "authorized"
