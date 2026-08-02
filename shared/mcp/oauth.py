"""OAuth 2.1 para servidores MCP remotos (spec de autorização do MCP).

Fluxo implementado, para servidores HTTP que respondem 401:

1. requisição sem token -> 401 com `WWW-Authenticate: Bearer resource_metadata="..."`
2. Protected Resource Metadata (RFC 9728) -> descobre o(s) authorization server(s)
3. Authorization Server Metadata (RFC 8414 / OIDC discovery) -> endpoints
4. Dynamic Client Registration (RFC 7591) -> client_id (quando o AS suporta)
5. Authorization Code + PKCE (S256) com `resource` (RFC 8707)
6. troca do código por access_token/refresh_token
7. refresh automático quando o access_token expira

As funções de parsing/montagem são puras (testáveis sem rede); as que fazem I/O
estão isoladas no fim do módulo.
"""
import base64
import hashlib
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urljoin, urlparse

import httpx

from shared.logging import get_logger

logger = get_logger("shared.mcp.oauth")

HTTP_TIMEOUT_SECONDS = 20.0
# Margem para considerar o token "quase expirado" e renovar antes de usar.
EXPIRY_SKEW_SECONDS = 60
CLIENT_NAME = "Software Factory"
# Escopo pedido quando o servidor não declara escopos suportados.
DEFAULT_SCOPE = ""


class MCPOAuthError(Exception):
    """Falha em qualquer etapa do fluxo OAuth com o servidor MCP."""


# ----------------------------- funções puras -----------------------------


def generate_pkce() -> tuple[str, str]:
    """Gera (code_verifier, code_challenge) para PKCE S256."""
    verifier = base64.urlsafe_b64encode(os.urandom(64)).decode().rstrip("=")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def parse_www_authenticate(header: str | None) -> dict[str, str]:
    """Extrai os parâmetros de um header WWW-Authenticate Bearer.

    Ex.: 'Bearer error="invalid_token", resource_metadata="https://x/.well-known/y"'
    """
    if not header:
        return {}
    return {
        match.group(1).lower(): match.group(2)
        for match in re.finditer(r'([A-Za-z_\-]+)\s*=\s*"([^"]*)"', header)
    }


def protected_resource_metadata_urls(resource_url: str) -> list[str]:
    """URLs candidatas de Protected Resource Metadata (RFC 9728).

    A spec define /.well-known/oauth-protected-resource na raiz, com o path do
    recurso anexado; mantemos as duas variantes por compatibilidade.
    """
    parsed = urlparse(resource_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    path = (parsed.path or "").rstrip("/")
    candidates = []
    if path:
        candidates.append(f"{origin}/.well-known/oauth-protected-resource{path}")
    candidates.append(f"{origin}/.well-known/oauth-protected-resource")
    return candidates


def authorization_server_metadata_urls(issuer: str) -> list[str]:
    """URLs candidatas de metadata do authorization server.

    RFC 8414 insere o well-known entre host e path; OIDC o anexa ao final.
    """
    issuer = issuer.rstrip("/")
    parsed = urlparse(issuer)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    path = (parsed.path or "").rstrip("/")
    candidates = []
    if path:
        candidates.append(f"{origin}/.well-known/oauth-authorization-server{path}")
        candidates.append(f"{issuer}/.well-known/oauth-authorization-server")
        candidates.append(f"{issuer}/.well-known/openid-configuration")
        candidates.append(f"{origin}/.well-known/openid-configuration{path}")
    else:
        candidates.append(f"{origin}/.well-known/oauth-authorization-server")
        candidates.append(f"{origin}/.well-known/openid-configuration")
    # remove duplicatas preservando a ordem
    seen: set[str] = set()
    return [c for c in candidates if not (c in seen or seen.add(c))]


def select_authorization_server(prm: dict) -> str:
    servers = prm.get("authorization_servers") or []
    if not servers:
        raise MCPOAuthError(
            "Protected Resource Metadata sem 'authorization_servers'; "
            "o servidor MCP não indicou como autorizar."
        )
    return str(servers[0])


def canonical_resource(resource_url: str) -> str:
    """Identificador canônico do recurso para o parâmetro `resource` (RFC 8707)."""
    parsed = urlparse(resource_url)
    path = (parsed.path or "").rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def pick_scope(asm: dict, prm: dict | None = None) -> str:
    """Escopo a solicitar: prioriza o declarado pelo recurso, senão o do AS."""
    for source in (prm or {}, asm):
        scopes = source.get("scopes_supported")
        if scopes:
            return " ".join(str(s) for s in scopes)
    return DEFAULT_SCOPE


def build_authorization_url(
    *,
    asm: dict,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    resource: str,
    scope: str = "",
) -> str:
    endpoint = asm.get("authorization_endpoint")
    if not endpoint:
        raise MCPOAuthError("Authorization Server Metadata sem 'authorization_endpoint'")
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "resource": resource,
    }
    if scope:
        params["scope"] = scope
    separator = "&" if urlparse(endpoint).query else "?"
    return f"{endpoint}{separator}{urlencode(params)}"


def registration_payload(redirect_uri: str, *, scope: str = "") -> dict:
    payload = {
        "client_name": CLIENT_NAME,
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",  # cliente público com PKCE
        "application_type": "web",
    }
    if scope:
        payload["scope"] = scope
    return payload


def tokens_from_response(payload: dict, *, now: datetime | None = None) -> dict:
    """Normaliza a resposta do token endpoint."""
    access_token = payload.get("access_token")
    if not access_token:
        raise MCPOAuthError(f"Resposta do token endpoint sem access_token: {payload}")
    now = now or datetime.now(timezone.utc)
    expires_in = payload.get("expires_in")
    expires_at = None
    if expires_in is not None:
        try:
            expires_at = now + timedelta(seconds=int(expires_in))
        except (TypeError, ValueError):
            expires_at = None
    return {
        "access_token": access_token,
        "refresh_token": payload.get("refresh_token"),
        "expires_at": expires_at,
        "scope": payload.get("scope") or "",
        "token_type": payload.get("token_type") or "Bearer",
    }


def is_token_expired(expires_at: datetime | None, *, now: datetime | None = None) -> bool:
    """Token sem expiração declarada é tratado como válido (renova no 401)."""
    if expires_at is None:
        return False
    now = now or datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= now + timedelta(seconds=EXPIRY_SKEW_SECONDS)


# ------------------------------ funções de I/O ------------------------------


async def _get_json(client: httpx.AsyncClient, url: str) -> dict:
    response = await client.get(url, headers={"Accept": "application/json"})
    if response.status_code >= 400:
        raise MCPOAuthError(f"HTTP {response.status_code} em {url}")
    try:
        return response.json()
    except ValueError as exc:
        raise MCPOAuthError(f"Resposta não-JSON em {url}") from exc


async def fetch_protected_resource_metadata(
    resource_url: str, *, hint_url: str | None = None
) -> dict:
    """Busca a Protected Resource Metadata do servidor MCP."""
    candidates = ([hint_url] if hint_url else []) + protected_resource_metadata_urls(resource_url)
    errors = []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=True) as client:
        for url in candidates:
            try:
                return await _get_json(client, url)
            except (MCPOAuthError, httpx.HTTPError) as exc:
                errors.append(f"{url}: {exc}")
    raise MCPOAuthError("Não foi possível obter a metadata do recurso. " + "; ".join(errors))


async def fetch_authorization_server_metadata(issuer: str) -> dict:
    errors = []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=True) as client:
        for url in authorization_server_metadata_urls(issuer):
            try:
                metadata = await _get_json(client, url)
                if metadata.get("authorization_endpoint") and metadata.get("token_endpoint"):
                    return metadata
                errors.append(f"{url}: metadata incompleta")
            except (MCPOAuthError, httpx.HTTPError) as exc:
                errors.append(f"{url}: {exc}")
    raise MCPOAuthError(
        f"Não foi possível obter a metadata do authorization server ({issuer}). "
        + "; ".join(errors)
    )


async def register_client(registration_endpoint: str, redirect_uri: str, *, scope: str = "") -> dict:
    """Dynamic Client Registration (RFC 7591)."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=True) as client:
        response = await client.post(
            registration_endpoint,
            json=registration_payload(redirect_uri, scope=scope),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
    if response.status_code >= 400:
        raise MCPOAuthError(
            f"Registro dinâmico de cliente falhou (HTTP {response.status_code}): "
            f"{response.text[:300]}"
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise MCPOAuthError("Resposta não-JSON no registro dinâmico de cliente") from exc
    if not payload.get("client_id"):
        raise MCPOAuthError(f"Registro dinâmico sem client_id: {payload}")
    return payload


async def _post_token(token_endpoint: str, data: dict, client_secret: str | None) -> dict:
    if client_secret:
        data = {**data, "client_secret": client_secret}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=True) as client:
        response = await client.post(
            token_endpoint,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
    if response.status_code >= 400:
        raise MCPOAuthError(
            f"Token endpoint respondeu HTTP {response.status_code}: {response.text[:300]}"
        )
    try:
        return response.json()
    except ValueError as exc:
        raise MCPOAuthError("Resposta não-JSON do token endpoint") from exc


async def exchange_code(
    *,
    token_endpoint: str,
    code: str,
    code_verifier: str,
    client_id: str,
    redirect_uri: str,
    resource: str,
    client_secret: str | None = None,
) -> dict:
    payload = await _post_token(
        token_endpoint,
        {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "resource": resource,
        },
        client_secret,
    )
    return tokens_from_response(payload)


async def refresh_access_token(
    *,
    token_endpoint: str,
    refresh_token: str,
    client_id: str,
    resource: str,
    scope: str = "",
    client_secret: str | None = None,
) -> dict:
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "resource": resource,
    }
    if scope:
        data["scope"] = scope
    payload = await _post_token(token_endpoint, data, client_secret)
    tokens = tokens_from_response(payload)
    # Alguns servidores não devolvem refresh_token na renovação: mantém o atual.
    tokens["refresh_token"] = tokens["refresh_token"] or refresh_token
    return tokens
