"""Seed de demonstração: workspace, projeto, itens e 2 sprints com histórico real.

Todo o histórico e gerado pelos próprios casos de uso com um FrozenClock,
garantindo que o event log (e portanto o burndown) seja fiel.

Uso:
    uv run python scripts/seed_demo.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, date, datetime, time, timedelta

from cadencia.identity.application.use_cases import CreateWorkspace, RegisterUser
from cadencia.identity.infrastructure import orm as identity_orm  # noqa: F401
from cadencia.identity.infrastructure.repositories import (
    SqlMembershipRepository,
    SqlOrganizationRepository,
    SqlUserRepository,
    SqlWorkspaceRepository,
)
from cadencia.identity.infrastructure.security import Argon2PasswordHasher
from cadencia.integrations.infrastructure import orm as integrations_orm  # noqa: F401
from cadencia.platform import orm as platform_orm  # noqa: F401
from cadencia.platform.config import get_settings
from cadencia.platform.db import Base, build_engine, build_session_factory
from cadencia.shared.clock import FrozenClock
from cadencia.shared.domain import AuditInfo
from cadencia.work.application.use_cases import (
    AssignWorkItemToSprint,
    CompleteSprint,
    CreateProject,
    CreateSprint,
    CreateWorkItem,
    MoveWorkItem,
    StartSprint,
    UpdateWorkItem,
)
from cadencia.work.domain.value_objects import Priority, ProjectMode, WorkItemType
from cadencia.work.infrastructure import orm as work_orm  # noqa: F401
from cadencia.work.infrastructure.repositories import (
    SqlAssignmentRepository,
    SqlBoardRepository,
    SqlProjectRepository,
    SqlSprintRepository,
    SqlWorkItemRepository,
)

DEMO_EMAIL = "demo@cadencia.dev"
DEMO_PASSWORD = "cadencia-demo-2026"
DEMO_NAME = "Demo Cadencia"

DAY_START = time(9, 0)


def moment(day: date, hour: int = 9) -> datetime:
    return datetime.combine(day, time(hour, 0), tzinfo=UTC)


async def _move_to_category(
    move: MoveWorkItem,
    board,
    *,
    workspace_id,
    item_id,
    category: str,
    clock: FrozenClock,
    index: int = 10**6,
) -> None:
    column = next(
        column
        for column in sorted(board.columns, key=lambda column: column.position)
        if column.category.value == category
    )
    await move.execute(
        workspace_id=workspace_id,
        item_id=item_id,
        target_column_id=column.id,
        target_index=index,
    )
    _ = clock


async def seed() -> None:
    settings = get_settings()
    if settings.is_production and "--force" not in sys.argv:
        print(
            "Recusando rodar o seed de demonstração em produção "
            "(use --force se for realmente isso que você quer)."
        )
        return
    engine = build_engine(settings)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = build_session_factory(engine)
    today = datetime.now(UTC).date()

    async with factory() as session:
        users = SqlUserRepository(session)
        if await users.find_by_email(DEMO_EMAIL) is not None:
            print(f"Seed ignorado: {DEMO_EMAIL} já existe.")
            await engine.dispose()
            return

        users = SqlUserRepository(session)
        organizations = SqlOrganizationRepository(session)
        workspaces = SqlWorkspaceRepository(session)
        memberships = SqlMembershipRepository(session)
        projects = SqlProjectRepository(session)
        boards = SqlBoardRepository(session)
        items = SqlWorkItemRepository(session)
        sprints = SqlSprintRepository(session)
        assignments = SqlAssignmentRepository(session)

        start = moment(today - timedelta(days=21))
        clock = FrozenClock(start)
        session.info["clock"] = clock

        user = await RegisterUser(users, Argon2PasswordHasher(), clock).execute(
            email=DEMO_EMAIL, name=DEMO_NAME, password=DEMO_PASSWORD, locale="pt-BR"
        )
        session.info["audit"] = AuditInfo(actor_id=user.id, source="local")
        workspace_view = await CreateWorkspace(
            organizations, workspaces, memberships, clock
        ).execute(user=user, name="Acme Studio", timezone="America/Sao_Paulo")
        workspace_id = workspace_view.id

        project_view = await CreateProject(projects, boards, clock).execute(
            workspace_id=workspace_id, name="App Mobile", key="APP", mode=ProjectMode.POINTS
        )
        board = await boards.get_by_project(project_view.id)
        assert board is not None

        create_item = CreateWorkItem(projects, boards, items, clock)
        move_item = MoveWorkItem(projects, boards, items, clock)
        assign_item = AssignWorkItemToSprint(projects, boards, items, sprints, assignments, clock)
        update_item = UpdateWorkItem(projects, boards, items, clock)

        backlog_specs = [
            ("Sync offline", WorkItemType.STORY, 13, Priority.HIGH),
            ("Push notifications", WorkItemType.STORY, 8, Priority.MEDIUM),
            ("Tema escuro no app", WorkItemType.STORY, 5, Priority.MEDIUM),
            ("Widgets de onboarding", WorkItemType.TASK, 3, Priority.LOW),
        ]
        for title, item_type, points, priority in backlog_specs:
            await create_item.execute(
                workspace_id=workspace_id,
                project_id=project_view.id,
                item_type=item_type,
                title=title,
                story_points=points,
                priority=priority,
            )

        sprint1_items = [
            ("Login com email", WorkItemType.STORY, 5),
            ("Dashboard de métricas", WorkItemType.STORY, 8),
            ("API de sprints", WorkItemType.TASK, 3),
            ("Design system ink", WorkItemType.TASK, 5),
            ("Corrigir crash no login", WorkItemType.BUG, 2),
        ]
        sprint1_ids: dict[str, object] = {}
        for title, item_type, points in sprint1_items:
            view = await create_item.execute(
                workspace_id=workspace_id,
                project_id=project_view.id,
                item_type=item_type,
                title=title,
                story_points=points,
            )
            sprint1_ids[title] = view.id

        sprint1 = await CreateSprint(projects, boards, sprints, clock).execute(
            workspace_id=workspace_id,
            project_id=project_view.id,
            name="Sprint 1 — Fundação",
            goal="Entregar login e dashboard com dados reais",
            start_date=today - timedelta(days=21),
            end_date=today - timedelta(days=8),
        )
        for item_id in sprint1_ids.values():
            await assign_item.execute(
                workspace_id=workspace_id, item_id=item_id, sprint_id=sprint1.id
            )
        await StartSprint(projects, boards, items, sprints, clock).execute(
            workspace_id=workspace_id, sprint_id=sprint1.id
        )

        clock.set(moment(today - timedelta(days=19)))
        await _move_to_category(
            move_item,
            board,
            workspace_id=workspace_id,
            item_id=sprint1_ids["API de sprints"],
            category="IN_PROGRESS",
            clock=clock,
        )
        clock.set(moment(today - timedelta(days=17)))
        await _move_to_category(
            move_item,
            board,
            workspace_id=workspace_id,
            item_id=sprint1_ids["Login com email"],
            category="IN_PROGRESS",
            clock=clock,
        )
        clock.set(moment(today - timedelta(days=16)))
        await _move_to_category(
            move_item,
            board,
            workspace_id=workspace_id,
            item_id=sprint1_ids["API de sprints"],
            category="DONE",
            clock=clock,
        )
        clock.set(moment(today - timedelta(days=14)))
        await _move_to_category(
            move_item,
            board,
            workspace_id=workspace_id,
            item_id=sprint1_ids["Login com email"],
            category="DONE",
            clock=clock,
        )
        clock.set(moment(today - timedelta(days=11)))
        await _move_to_category(
            move_item,
            board,
            workspace_id=workspace_id,
            item_id=sprint1_ids["Dashboard de métricas"],
            category="IN_PROGRESS",
            clock=clock,
        )
        clock.set(moment(today - timedelta(days=10)))
        await _move_to_category(
            move_item,
            board,
            workspace_id=workspace_id,
            item_id=sprint1_ids["Corrigir crash no login"],
            category="IN_PROGRESS",
            clock=clock,
        )
        await _move_to_category(
            move_item,
            board,
            workspace_id=workspace_id,
            item_id=sprint1_ids["Dashboard de métricas"],
            category="DONE",
            clock=clock,
        )
        clock.set(moment(today - timedelta(days=9)))
        await _move_to_category(
            move_item,
            board,
            workspace_id=workspace_id,
            item_id=sprint1_ids["Corrigir crash no login"],
            category="DONE",
            clock=clock,
        )

        clock.set(moment(today - timedelta(days=7)))
        sprint2 = await CreateSprint(projects, boards, sprints, clock).execute(
            workspace_id=workspace_id,
            project_id=project_view.id,
            name="Sprint 2 — Retenção",
            goal="Ativar tema escuro e notificações com qualidade",
            start_date=today - timedelta(days=7),
            end_date=today + timedelta(days=6),
        )
        await CompleteSprint(projects, boards, items, sprints, assignments, clock).execute(
            workspace_id=workspace_id, sprint_id=sprint1.id, target_sprint_id=sprint2.id
        )

        new_in_sprint2 = await create_item.execute(
            workspace_id=workspace_id,
            project_id=project_view.id,
            item_type=WorkItemType.STORY,
            title="Tema escuro no app",
            story_points=5,
        )
        push = await create_item.execute(
            workspace_id=workspace_id,
            project_id=project_view.id,
            item_type=WorkItemType.STORY,
            title="Push notifications",
            story_points=8,
        )
        for item_view in (new_in_sprint2, push):
            await assign_item.execute(
                workspace_id=workspace_id, item_id=item_view.id, sprint_id=sprint2.id
            )
        await StartSprint(projects, boards, items, sprints, clock).execute(
            workspace_id=workspace_id, sprint_id=sprint2.id
        )

        clock.set(moment(today - timedelta(days=5)))
        await _move_to_category(
            move_item,
            board,
            workspace_id=workspace_id,
            item_id=new_in_sprint2.id,
            category="IN_PROGRESS",
            clock=clock,
        )
        clock.set(moment(today - timedelta(days=4)))
        await _move_to_category(
            move_item,
            board,
            workspace_id=workspace_id,
            item_id=push.id,
            category="IN_PROGRESS",
            clock=clock,
        )
        await update_item.execute(workspace_id=workspace_id, item_id=push.id, assignee_id=user.id)

        clock.set(moment(today - timedelta(days=3)))
        hotfix = await create_item.execute(
            workspace_id=workspace_id,
            project_id=project_view.id,
            item_type=WorkItemType.BUG,
            title="Hotfix: evento de analytics duplicado",
            story_points=2,
            priority=Priority.HIGHEST,
        )
        await assign_item.execute(
            workspace_id=workspace_id, item_id=hotfix.id, sprint_id=sprint2.id
        )
        await _move_to_category(
            move_item,
            board,
            workspace_id=workspace_id,
            item_id=hotfix.id,
            category="IN_PROGRESS",
            clock=clock,
        )
        clock.set(moment(today - timedelta(days=2)))
        await _move_to_category(
            move_item,
            board,
            workspace_id=workspace_id,
            item_id=new_in_sprint2.id,
            category="DONE",
            clock=clock,
        )
        clock.set(moment(today - timedelta(days=1)))
        await _move_to_category(
            move_item,
            board,
            workspace_id=workspace_id,
            item_id=hotfix.id,
            category="DONE",
            clock=clock,
        )

        await session.commit()

    await engine.dispose()
    print("Seed concluído.")
    print(f"  usuário: {DEMO_EMAIL}")
    print(f"  senha:   {DEMO_PASSWORD}")
    print("  workspace: Acme Studio (slug acme-studio)")


if __name__ == "__main__":
    asyncio.run(seed())
