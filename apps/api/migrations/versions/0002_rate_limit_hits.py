"""Tabela de rate limit do auth.

A 0001 e metadata-driven (create_all do metadata atual), entao em um banco
novo esta tabela Ja nasce por la; aqui garantimos a criacao em bancos que
foram migrados antes desta revisao. Por isso o guard de existencia.

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "rate_limit_hits" not in inspector.get_table_names():
        op.create_table(
            "rate_limit_hits",
            sa.Column("key", sa.String(length=255), primary_key=True),
            sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "rate_limit_hits" in inspector.get_table_names():
        op.drop_table("rate_limit_hits")
