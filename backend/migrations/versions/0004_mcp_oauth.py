"""Autorização OAuth 2.1 para servidores MCP remotos.

Servidores MCP hospedados (ex.: mcp.notion.com) são OAuth-only: não aceitam
token estático e exigem o fluxo authorization code + PKCE, com descoberta de
metadata (RFC 9728/8414) e registro dinâmico de cliente (RFC 7591). Estas
colunas guardam a metadata descoberta, as credenciais do cliente, os tokens e
o estado da autorização em andamento.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

COLUMNS = [
    ("oauth_metadata", sa.JSON(), {"nullable": False, "server_default": "{}"}),
    ("oauth_client_id", sa.String(512), {}),
    ("oauth_client_secret", sa.String(1024), {}),
    ("oauth_scope", sa.String(1024), {}),
    ("oauth_resource", sa.String(1024), {}),
    ("oauth_access_token", sa.Text(), {}),
    ("oauth_refresh_token", sa.Text(), {}),
    ("oauth_expires_at", sa.DateTime(timezone=True), {}),
    ("oauth_state", sa.String(128), {}),
    ("oauth_code_verifier", sa.String(256), {}),
]


def upgrade() -> None:
    for name, type_, kwargs in COLUMNS:
        op.add_column("mcp_servers", sa.Column(name, type_, **kwargs))
    # O callback OAuth localiza o servidor pelo `state`, então o índice é
    # funcional, não só otimização.
    op.create_index("ix_mcp_servers_oauth_state", "mcp_servers", ["oauth_state"])


def downgrade() -> None:
    op.drop_index("ix_mcp_servers_oauth_state", table_name="mcp_servers")
    for name, _type, _kwargs in reversed(COLUMNS):
        op.drop_column("mcp_servers", name)
