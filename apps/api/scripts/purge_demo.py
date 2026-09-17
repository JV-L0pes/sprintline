"""Remove os dados de demonstracao (usuario demo, workspaces e eventos).

Uso:
    CADENCIA_DATABASE_URL=<url> uv run python scripts/purge_demo.py --yes

Exclui: memberships/sessions/invites do usuario demo, os workspaces em que ele
e owner (cascata em projetos/boards/itens/sprints/integracoes), os eventos
desses workspaces (a tabela de eventos nao tem FK, entao e explicito) e as
organizacoes orfas.
"""

from __future__ import annotations

import asyncio
import sys
import uuid

import sqlalchemy as sa

from cadencia.identity.infrastructure.orm import (
    MembershipRow,
    OrganizationRow,
    UserRow,
    WorkspaceRow,
)
from cadencia.platform.config import get_settings
from cadencia.platform.db import build_engine, build_session_factory
from cadencia.platform.orm import DomainEventRow

DEMO_EMAIL = "demo@cadencia.dev"


async def purge() -> None:
    if "--yes" not in sys.argv:
        print("Passa --yes para confirmar a remocao dos dados de demonstracao.")
        return
    settings = get_settings()
    engine = build_engine(settings)
    factory = build_session_factory(engine)
    async with factory() as session:
        user_id = (
            await session.execute(sa.select(UserRow.id).where(UserRow.email == DEMO_EMAIL))
        ).scalar_one_or_none()
        if user_id is None:
            print("Usuario demo nao existe; nada a remover.")
            await engine.dispose()
            return

        workspace_ids = (
            (
                await session.execute(
                    sa.select(MembershipRow.workspace_id).where(MembershipRow.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )
        removed_events = await _delete_events(session, workspace_ids)
        for workspace_id in workspace_ids:
            row = await session.get(WorkspaceRow, workspace_id)
            if row is not None:
                await session.delete(row)
        await session.flush()

        await session.execute(
            sa.delete(OrganizationRow).where(
                ~sa.exists(
                    sa.select(WorkspaceRow.id).where(
                        WorkspaceRow.organization_id == OrganizationRow.id
                    )
                )
            )
        )
        row = await session.get(UserRow, user_id)
        if row is not None:
            await session.delete(row)
        await session.commit()
        print(
            f"Removidos: usuario demo, {len(workspace_ids)} workspaces, {removed_events} eventos."
        )
    await engine.dispose()


async def _delete_events(session: object, workspace_ids: list[uuid.UUID]) -> int:
    if not workspace_ids:
        return 0
    result = await session.execute(  # type: ignore[attr-defined]
        sa.delete(DomainEventRow).where(DomainEventRow.workspace_id.in_(workspace_ids))
    )
    return int(result.rowcount or 0)


if __name__ == "__main__":
    asyncio.run(purge())
