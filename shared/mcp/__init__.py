"""Integração com servidores MCP (Model Context Protocol).

Fase 1: conexão, handshake, descoberta de ferramentas (`tools/list`) e
autorização OAuth 2.1 para servidores remotos, usados pela tela de
configuração de MCP. A execução de ferramentas pelos agentes (`tools/call`
dentro de um loop de tool calling no runtime) é a fase 2.
"""
from shared.mcp.client import (
    MCPAuthorizationRequired,
    MCPConnectionError,
    MCPServerConfig,
    call_tool,
    discover_tools,
)
from shared.mcp.oauth import MCPOAuthError

__all__ = [
    "MCPAuthorizationRequired",
    "MCPConnectionError",
    "MCPOAuthError",
    "MCPServerConfig",
    "call_tool",
    "discover_tools",
]
