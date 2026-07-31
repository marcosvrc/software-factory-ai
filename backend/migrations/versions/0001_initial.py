"""Esquema inicial: 13 entidades da seção 12 + usuários locais.

Revision ID: 0001
Revises:
Create Date: 2026-07-30
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db.base import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from app.db.base import Base
    import app.models  # noqa: F401

    Base.metadata.drop_all(bind=op.get_bind())
