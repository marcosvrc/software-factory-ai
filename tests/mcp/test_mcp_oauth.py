"""Testes do OAuth 2.1 para servidores MCP (shared/mcp/oauth.py).

Cobre PKCE, parsing do WWW-Authenticate, derivação das URLs de metadata
(RFC 9728/8414), montagem da URL de autorização com `resource` (RFC 8707),
payload de registro dinâmico (RFC 7591) e normalização/expiração de tokens.
"""
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from shared.mcp.oauth import (
    MCPOAuthError,
    authorization_server_metadata_urls,
    build_authorization_url,
    canonical_resource,
    generate_pkce,
    generate_state,
    is_token_expired,
    parse_www_authenticate,
    pick_scope,
    protected_resource_metadata_urls,
    registration_payload,
    select_authorization_server,
    tokens_from_response,
)

ASM = {
    "authorization_endpoint": "https://auth.example.com/authorize",
    "token_endpoint": "https://auth.example.com/token",
    "registration_endpoint": "https://auth.example.com/register",
}


def test_pkce_challenge_matches_verifier():
    verifier, challenge = generate_pkce()
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    assert challenge == expected
    assert "=" not in challenge


def test_pkce_verifier_length_within_spec():
    verifier, _ = generate_pkce()
    assert 43 <= len(verifier) <= 128


def test_pkce_and_state_are_unique_per_call():
    assert generate_pkce()[0] != generate_pkce()[0]
    assert generate_state() != generate_state()


def test_parse_www_authenticate_extracts_resource_metadata():
    header = (
        'Bearer error="invalid_token", error_description="Missing or invalid access token", '
        'resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource"'
    )
    params = parse_www_authenticate(header)
    assert params["error"] == "invalid_token"
    assert params["resource_metadata"] == (
        "https://mcp.example.com/.well-known/oauth-protected-resource"
    )


def test_parse_www_authenticate_handles_missing_header():
    assert parse_www_authenticate(None) == {}
    assert parse_www_authenticate("Bearer") == {}


def test_protected_resource_metadata_urls_include_path_variant():
    urls = protected_resource_metadata_urls("https://mcp.notion.com/mcp")
    assert urls[0] == "https://mcp.notion.com/.well-known/oauth-protected-resource/mcp"
    assert "https://mcp.notion.com/.well-known/oauth-protected-resource" in urls


def test_authorization_server_metadata_urls_follow_rfc8414_and_oidc():
    urls = authorization_server_metadata_urls("https://auth.example.com/tenant1")
    assert urls[0] == "https://auth.example.com/.well-known/oauth-authorization-server/tenant1"
    assert "https://auth.example.com/tenant1/.well-known/openid-configuration" in urls


def test_authorization_server_metadata_urls_without_path():
    urls = authorization_server_metadata_urls("https://auth.example.com")
    assert urls == [
        "https://auth.example.com/.well-known/oauth-authorization-server",
        "https://auth.example.com/.well-known/openid-configuration",
    ]


def test_select_authorization_server_picks_first():
    assert select_authorization_server({"authorization_servers": ["https://a", "https://b"]}) == (
        "https://a"
    )


def test_select_authorization_server_without_entry_raises():
    with pytest.raises(MCPOAuthError):
        select_authorization_server({})


def test_canonical_resource_strips_trailing_slash():
    assert canonical_resource("https://mcp.notion.com/mcp/") == "https://mcp.notion.com/mcp"
    assert canonical_resource("https://mcp.notion.com") == "https://mcp.notion.com"


def test_authorization_url_contains_pkce_and_resource():
    url = build_authorization_url(
        asm=ASM,
        client_id="cli-123",
        redirect_uri="http://localhost:8000/api/v1/mcp/oauth/callback",
        state="st",
        code_challenge="ch",
        resource="https://mcp.notion.com/mcp",
        scope="read write",
    )
    query = parse_qs(urlparse(url).query)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["cli-123"]
    assert query["code_challenge"] == ["ch"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["resource"] == ["https://mcp.notion.com/mcp"]
    assert query["state"] == ["st"]
    assert query["scope"] == ["read write"]


def test_authorization_url_preserves_existing_query():
    asm = {**ASM, "authorization_endpoint": "https://auth.example.com/authorize?tenant=x"}
    url = build_authorization_url(
        asm=asm,
        client_id="c",
        redirect_uri="http://localhost/cb",
        state="s",
        code_challenge="ch",
        resource="https://r",
    )
    query = parse_qs(urlparse(url).query)
    assert query["tenant"] == ["x"]
    assert query["client_id"] == ["c"]


def test_authorization_url_omits_empty_scope():
    url = build_authorization_url(
        asm=ASM,
        client_id="c",
        redirect_uri="http://localhost/cb",
        state="s",
        code_challenge="ch",
        resource="https://r",
        scope="",
    )
    assert "scope=" not in url


def test_authorization_url_without_endpoint_raises():
    with pytest.raises(MCPOAuthError):
        build_authorization_url(
            asm={},
            client_id="c",
            redirect_uri="http://localhost/cb",
            state="s",
            code_challenge="ch",
            resource="https://r",
        )


def test_registration_payload_is_public_client_with_pkce():
    payload = registration_payload("http://localhost:8000/cb", scope="read")
    assert payload["redirect_uris"] == ["http://localhost:8000/cb"]
    assert payload["token_endpoint_auth_method"] == "none"
    assert "authorization_code" in payload["grant_types"]
    assert "refresh_token" in payload["grant_types"]
    assert payload["scope"] == "read"


def test_pick_scope_prefers_resource_metadata():
    assert pick_scope({"scopes_supported": ["a"]}, {"scopes_supported": ["b", "c"]}) == "b c"


def test_pick_scope_falls_back_to_authorization_server():
    assert pick_scope({"scopes_supported": ["a"]}, {}) == "a"


def test_pick_scope_without_declaration_is_empty():
    assert pick_scope({}, {}) == ""


def test_tokens_from_response_computes_expiry():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tokens = tokens_from_response(
        {"access_token": "at", "refresh_token": "rt", "expires_in": 3600, "scope": "read"}, now=now
    )
    assert tokens["access_token"] == "at"
    assert tokens["refresh_token"] == "rt"
    assert tokens["expires_at"] == now + timedelta(seconds=3600)
    assert tokens["scope"] == "read"


def test_tokens_from_response_without_expiry():
    tokens = tokens_from_response({"access_token": "at"})
    assert tokens["expires_at"] is None
    assert tokens["refresh_token"] is None


def test_tokens_from_response_without_access_token_raises():
    with pytest.raises(MCPOAuthError):
        tokens_from_response({"error": "invalid_grant"})


def test_token_without_expiry_is_not_expired():
    assert is_token_expired(None) is False


def test_expired_token_is_detected():
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    assert is_token_expired(past) is True


def test_token_expiring_within_skew_is_treated_as_expired():
    """Renova um pouco antes de expirar para evitar corrida com o servidor."""
    almost = datetime.now(timezone.utc) + timedelta(seconds=30)
    assert is_token_expired(almost) is True


def test_valid_token_is_not_expired():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    assert is_token_expired(future) is False


def test_naive_datetime_is_treated_as_utc():
    """Postgres pode devolver datetime sem tzinfo; comparar com um aware
    levantaria TypeError e quebraria a renovação do token."""
    past_naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    assert is_token_expired(past_naive) is True
