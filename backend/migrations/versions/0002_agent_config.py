"""Configuração editável de agentes: snapshot padrão + etapas do pipeline.

Antes desta migração, `agent_definitions.configuration` era sobrescrito a cada
restart do orquestrador (sync_agent_definitions) com o conteúdo do YAML, de
modo que qualquer customização feita via API era perdida. Agora:

- `configuration` passa a ser preservado no sync (edição do usuário vence);
- `default_configuration` guarda o snapshot do YAML para permitir "restaurar
  padrão" sem depender dos arquivos em disco (a imagem do backend não inclui
  agents/);
- `stages` lista as etapas do pipeline em que o agente participa, publicado
  pelo orquestrador a partir de STAGE_AGENTS, para exibição na UI.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_definitions",
        sa.Column("default_configuration", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "agent_definitions",
        sa.Column("stages", sa.JSON(), nullable=False, server_default="[]"),
    )
    # Backfill: até o próximo sync do orquestrador, o padrão é a configuração
    # atual (que nesse momento ainda é idêntica ao YAML).
    op.execute("UPDATE agent_definitions SET default_configuration = configuration")


def downgrade() -> None:
    op.drop_column("agent_definitions", "stages")
    op.drop_column("agent_definitions", "default_configuration")
