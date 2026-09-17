"""Schema inicial (metadata-driven).

A primeira migracao cria o schema completo a partir do metadata declarativo —
garantindo paridade total com os modelos. Migracao geradas a partir da 0002
devem ser produzidas com `alembic revision --autogenerate` contra Postgres.

Revision ID: 0001
Revises:
"""

from __future__ import annotations

from alembic import op

from cadencia.identity.infrastructure import orm as identity_orm  # noqa: F401
from cadencia.integrations.infrastructure import orm as integrations_orm  # noqa: F401
from cadencia.platform import orm as platform_orm  # noqa: F401
from cadencia.platform.db import Base
from cadencia.work.infrastructure import orm as work_orm  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
