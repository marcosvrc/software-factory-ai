"""Servidores MCP (Model Context Protocol) configuráveis.

Fase 1: cadastro dos servidores + resultado da última descoberta de
ferramentas (`tools/list`). O vínculo "quais MCPs cada agente pode usar" fica
em `agent_definitions.configuration["mcp_servers"]`, junto do restante da
configuração editável do agente.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_servers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("transport", sa.String(16), nullable=False, server_default="stdio"),
        sa.Column("command", sa.String(512)),
        sa.Column("args", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("env", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("url", sa.String(1024)),
        sa.Column("headers", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="30"),
        # Servidores nascem desabilitados: um servidor stdio é um comando
        # arbitrário executado no container, então habilitar é uma decisão
        # explícita de quem administra a fábrica.
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tools", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("last_status", sa.String(32)),
        sa.Column("last_error", sa.Text()),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("mcp_servers")
