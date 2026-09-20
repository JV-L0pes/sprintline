"""Casos de uso do contexto work."""

from __future__ import annotations

import uuid
from datetime import date

from cadencia.shared.clock import Clock
from cadencia.shared.errors import ConflictError, NotFoundError
from cadencia.shared.ids import uuid7
from cadencia.work.application.dto import (
    BoardView,
    ColumnView,
    MoveResult,
    ProjectView,
    SprintView,
    WorkItemView,
)
from cadencia.work.domain.entities import Board, Project, Sprint, WorkItem
from cadencia.work.domain.policies import WipVerdict, wip_verdict
from cadencia.work.domain.repositories import (
    AssignmentRecord,
    AssignmentRepository,
    BoardRepository,
    ProjectRepository,
    SprintRepository,
    WorkItemRepository,
)
from cadencia.work.domain.value_objects import (
    Priority,
    ProjectMode,
    SprintState,
    StatusCategory,
    WipEnforcement,
    WorkItemType,
)


def _category_of(board: Board, column_id: uuid.UUID) -> StatusCategory:
    column = board.column(column_id)
    if column is None:
        raise NotFoundError("Coluna não encontrada no board", code="COLUMN_NOT_FOUND")
    return column.category


def item_view(item: WorkItem, board: Board) -> WorkItemView:
    return WorkItemView(
        id=item.id,
        project_id=item.project_id,
        key=item.key,
        type=item.type,
        title=item.title,
        description=item.description,
        parent_id=item.parent_id,
        status_column_id=item.status_column_id,
        status_category=_category_of(board, item.status_column_id),
        story_points=item.story_points,
        priority=item.priority,
        assignee_id=item.assignee_id,
        sprint_id=item.sprint_id,
        position=item.position,
        due_date=item.due_date,
        created_at=item.created_at,
        updated_at=item.updated_at,
        done_at=item.done_at,
        first_in_progress_at=item.first_in_progress_at,
        version=item.version,
    )


def sprint_view(sprint: Sprint, items: list[WorkItem]) -> SprintView:
    countable = [item for item in items if item.type is not WorkItemType.SUBTASK]
    return SprintView(
        id=sprint.id,
        board_id=sprint.board_id,
        name=sprint.name,
        goal=sprint.goal,
        state=sprint.state,
        start_date=sprint.start_date,
        end_date=sprint.end_date,
        completed_at=sprint.completed_at,
        total_items=len(items),
        done_items=sum(1 for item in items if item.done_at is not None),
        total_points=sum(item.story_points or 0 for item in countable),
        done_points=sum(item.story_points or 0 for item in countable if item.done_at is not None),
    )


def project_view(project: Project) -> ProjectView:
    return ProjectView(
        id=project.id,
        name=project.name,
        key=project.key,
        mode=project.mode,
        wip_enforcement=project.wip_enforcement,
        created_at=project.created_at,
    )


async def _load_context(
    *,
    projects: ProjectRepository,
    boards: BoardRepository,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
) -> tuple[Project, Board]:
    project = await projects.get(project_id, workspace_id)
    if project is None:
        raise NotFoundError("Projeto não encontrado", code="PROJECT_NOT_FOUND")
    board = await boards.get_by_project(project.id)
    if board is None:
        raise NotFoundError("Board não encontrado", code="BOARD_NOT_FOUND")
    return project, board


class CreateProject:
    def __init__(
        self,
        projects: ProjectRepository,
        boards: BoardRepository,
        clock: Clock,
    ) -> None:
        self._projects = projects
        self._boards = boards
        self._clock = clock

    async def execute(
        self,
        *,
        workspace_id: uuid.UUID,
        name: str,
        key: str,
        mode: ProjectMode = ProjectMode.POINTS,
        wip_enforcement: WipEnforcement = WipEnforcement.SOFT,
    ) -> ProjectView:
        from cadencia.work.domain.value_objects import normalize_project_key

        normalized_key = normalize_project_key(key)
        if await self._projects.key_exists(workspace_id, normalized_key):
            raise ConflictError(
                f"Já existe projeto com a chave {normalized_key}", code="PROJECT_KEY_EXISTS"
            )
        project = Project.create(
            workspace_id=workspace_id,
            name=name,
            key=normalized_key,
            mode=mode,
            wip_enforcement=wip_enforcement,
            now=self._clock.now(),
        )
        await self._projects.add(project)
        board = Board.with_default_columns(project_id=project.id, name=f"{project.key} Board")
        await self._boards.add(board)
        return project_view(project)


class ListProjects:
    def __init__(self, projects: ProjectRepository) -> None:
        self._projects = projects

    async def execute(self, *, workspace_id: uuid.UUID) -> list[ProjectView]:
        projects = await self._projects.list_for_workspace(workspace_id)
        return [project_view(project) for project in projects]


def board_view(project: Project, board: Board, work_items: list[WorkItem]) -> BoardView:
    views = [item_view(item, board) for item in work_items]
    columns = [
        ColumnView(
            id=column.id,
            name=column.name,
            position=column.position,
            category=column.category,
            wip_limit=column.wip_limit,
            item_count=sum(1 for view in views if view.status_column_id == column.id),
        )
        for column in sorted(board.columns, key=lambda column: column.position)
    ]
    return BoardView(
        id=board.id, project_id=project.id, name=board.name, columns=columns, items=views
    )


class GetBoard:
    def __init__(
        self,
        projects: ProjectRepository,
        boards: BoardRepository,
        items: WorkItemRepository,
    ) -> None:
        self._projects = projects
        self._boards = boards
        self._items = items

    async def execute(self, *, workspace_id: uuid.UUID, project_id: uuid.UUID) -> BoardView:
        project, board = await _load_context(
            projects=self._projects,
            boards=self._boards,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        work_items = await self._items.list_for_project(project.id)
        return board_view(project, board, work_items)


class _BoardColumnsUseCase:
    """Base para operações de coluna: carrega contexto e devolve o board."""

    def __init__(
        self,
        projects: ProjectRepository,
        boards: BoardRepository,
        items: WorkItemRepository,
    ) -> None:
        self._projects = projects
        self._boards = boards
        self._items = items

    async def _save_and_view(
        self, *, workspace_id: uuid.UUID, project_id: uuid.UUID, board: Board
    ) -> BoardView:
        await self._boards.save(board)
        project, refreshed = await _load_context(
            projects=self._projects,
            boards=self._boards,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        work_items = await self._items.list_for_project(project.id)
        return board_view(project, refreshed, work_items)


class CreateBoardColumn(_BoardColumnsUseCase):
    async def execute(
        self,
        *,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        name: str,
        category: StatusCategory,
        wip_limit: int | None = None,
    ) -> BoardView:
        _, board = await _load_context(
            projects=self._projects,
            boards=self._boards,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        board.add_column(name=name, category=category, wip_limit=wip_limit)
        return await self._save_and_view(
            workspace_id=workspace_id, project_id=project_id, board=board
        )


class UpdateBoardColumn(_BoardColumnsUseCase):
    async def execute(
        self,
        *,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        column_id: uuid.UUID,
        name: str | None = None,
        category: StatusCategory | None = None,
        wip_limit: int | None = None,
        clear_wip: bool = False,
    ) -> BoardView:
        _, board = await _load_context(
            projects=self._projects,
            boards=self._boards,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        board.update_column(
            column_id, name=name, category=category, wip_limit=wip_limit, clear_wip=clear_wip
        )
        return await self._save_and_view(
            workspace_id=workspace_id, project_id=project_id, board=board
        )


class DeleteBoardColumn(_BoardColumnsUseCase):
    async def execute(
        self,
        *,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        column_id: uuid.UUID,
    ) -> BoardView:
        _, board = await _load_context(
            projects=self._projects,
            boards=self._boards,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        if board.column(column_id) is None:
            raise NotFoundError("Coluna não encontrada", code="COLUMN_NOT_FOUND")
        if await self._items.count_in_column(column_id) > 0:
            raise ConflictError(
                "Mova os itens desta coluna antes de remove-la", code="COLUMN_NOT_EMPTY"
            )
        board.remove_column(column_id)
        return await self._save_and_view(
            workspace_id=workspace_id, project_id=project_id, board=board
        )


class ReorderBoardColumns(_BoardColumnsUseCase):
    async def execute(
        self,
        *,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        column_ids: list[uuid.UUID],
    ) -> BoardView:
        _, board = await _load_context(
            projects=self._projects,
            boards=self._boards,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        board.reorder_columns(column_ids)
        return await self._save_and_view(
            workspace_id=workspace_id, project_id=project_id, board=board
        )


class ListItems:
    def __init__(
        self,
        projects: ProjectRepository,
        boards: BoardRepository,
        items: WorkItemRepository,
    ) -> None:
        self._projects = projects
        self._boards = boards
        self._items = items

    async def execute(
        self, *, workspace_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[WorkItemView]:
        project, board = await _load_context(
            projects=self._projects,
            boards=self._boards,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        work_items = await self._items.list_for_project(project.id)
        return [item_view(item, board) for item in work_items]


class ArchiveProject:
    """Arquivamento (soft delete): sai das listas, histórico permanece."""

    def __init__(self, projects: ProjectRepository, clock: Clock) -> None:
        self._projects = projects
        self._clock = clock

    async def execute(self, *, workspace_id: uuid.UUID, project_id: uuid.UUID) -> None:
        project = await self._projects.get(project_id, workspace_id)
        if project is None:
            raise NotFoundError("Projeto não encontrado", code="PROJECT_NOT_FOUND")
        project.archive(now=self._clock.now())
        await self._projects.save(project)


class ArchiveWorkItem:
    def __init__(
        self,
        projects: ProjectRepository,
        boards: BoardRepository,
        items: WorkItemRepository,
        clock: Clock,
    ) -> None:
        self._projects = projects
        self._boards = boards
        self._items = items
        self._clock = clock

    async def execute(self, *, workspace_id: uuid.UUID, item_id: uuid.UUID) -> None:
        item = await self._items.get(item_id)
        if item is None:
            raise NotFoundError("Item não encontrado", code="ITEM_NOT_FOUND")
        _, _board = await _load_context(
            projects=self._projects,
            boards=self._boards,
            workspace_id=workspace_id,
            project_id=item.project_id,
        )
        item.archive(now=self._clock.now())
        await self._items.save(item)


class CreateWorkItem:
    def __init__(
        self,
        projects: ProjectRepository,
        boards: BoardRepository,
        items: WorkItemRepository,
        clock: Clock,
    ) -> None:
        self._projects = projects
        self._boards = boards
        self._items = items
        self._clock = clock

    async def execute(
        self,
        *,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        item_type: WorkItemType,
        title: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        story_points: int | None = None,
        assignee_id: uuid.UUID | None = None,
        due_date: date | None = None,
        parent_id: uuid.UUID | None = None,
    ) -> WorkItemView:
        project, board = await _load_context(
            projects=self._projects,
            boards=self._boards,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        parent_type: WorkItemType | None = None
        if parent_id is not None:
            parent = await self._items.get(parent_id)
            if parent is None or parent.project_id != project.id or parent.archived_at is not None:
                raise NotFoundError("Item pai não encontrado", code="PARENT_NOT_FOUND")
            parent_type = parent.type

        number = project.allocate_item_number()
        todo_column = board.first_todo_column()
        item = WorkItem.create(
            project=project,
            item_type=item_type,
            title=title,
            description=description,
            priority=priority,
            story_points=story_points,
            assignee_id=assignee_id,
            due_date=due_date,
            parent_id=parent_id,
            parent_type=parent_type,
            todo_column_id=todo_column.id,
            position=await self._items.next_position(todo_column.id),
            key=f"{project.key}-{number}",
            now=self._clock.now(),
        )
        await self._projects.save(project)
        await self._items.add(item)
        return item_view(item, board)


class UpdateWorkItem:
    def __init__(
        self,
        projects: ProjectRepository,
        boards: BoardRepository,
        items: WorkItemRepository,
        clock: Clock,
    ) -> None:
        self._projects = projects
        self._boards = boards
        self._items = items
        self._clock = clock

    async def execute(
        self,
        *,
        workspace_id: uuid.UUID,
        item_id: uuid.UUID,
        expected_version: int | None = None,
        title: str | None = None,
        description: str | None = None,
        priority: Priority | None = None,
        assignee_id: uuid.UUID | None = None,
        clear_assignee: bool = False,
        story_points: int | None = None,
        clear_points: bool = False,
        due_date: date | None = None,
        clear_due_date: bool = False,
    ) -> WorkItemView:
        item = await self._items.get(item_id)
        if item is None:
            raise NotFoundError("Item não encontrado", code="ITEM_NOT_FOUND")
        project, board = await _load_context(
            projects=self._projects,
            boards=self._boards,
            workspace_id=workspace_id,
            project_id=item.project_id,
        )
        if expected_version is not None and expected_version != item.version:
            raise ConflictError(
                "Item foi alterado por outra pessoa; recarregue e tente novamente",
                code="STALE_VERSION",
            )
        _ = project
        item.update_details(
            now=self._clock.now(),
            title=title,
            description=description,
            priority=priority,
            assignee_id=assignee_id,
            clear_assignee=clear_assignee,
            story_points=story_points,
            clear_points=clear_points,
            due_date=due_date,
            clear_due_date=clear_due_date,
        )
        item.version += 1
        await self._items.save(item)
        return item_view(item, board)


class MoveWorkItem:
    def __init__(
        self,
        projects: ProjectRepository,
        boards: BoardRepository,
        items: WorkItemRepository,
        clock: Clock,
    ) -> None:
        self._projects = projects
        self._boards = boards
        self._items = items
        self._clock = clock

    async def execute(
        self,
        *,
        workspace_id: uuid.UUID,
        item_id: uuid.UUID,
        target_column_id: uuid.UUID,
        target_index: int,
        expected_version: int | None = None,
    ) -> MoveResult:
        item = await self._items.get(item_id)
        if item is None:
            raise NotFoundError("Item não encontrado", code="ITEM_NOT_FOUND")
        project, board = await _load_context(
            projects=self._projects,
            boards=self._boards,
            workspace_id=workspace_id,
            project_id=item.project_id,
        )
        if expected_version is not None and expected_version != item.version:
            raise ConflictError("Item desatualizado", code="STALE_VERSION")
        target_column = board.column(target_column_id)
        if target_column is None:
            raise NotFoundError("Coluna destino não encontrada", code="COLUMN_NOT_FOUND")

        current = await self._items.list_in_column(target_column.id)
        same_column = item.status_column_id == target_column.id
        if same_column:
            current = [candidate for candidate in current if candidate.id != item.id]
        verdict = wip_verdict(
            wip_limit=target_column.wip_limit,
            current_count=len(current),
            enforcement=project.wip_enforcement.value,
        )
        if verdict == WipVerdict.BLOCK:
            raise ConflictError(
                f"Coluna {target_column.name} atingiu o WIP limit de {target_column.wip_limit}",
                code="WIP_LIMIT_EXCEEDED",
            )

        index = max(0, min(target_index, len(current)))
        ordered = [*current[:index], item, *current[index:]]
        for position, candidate in enumerate(ordered, start=1):
            candidate.position = float(position)
        item.move_to(column=target_column, now=self._clock.now())
        item.version += 1
        await self._items.save_many(ordered)
        return MoveResult(item=item_view(item, board), wip_warning=verdict == WipVerdict.WARN)


class AssignWorkItemToSprint:
    def __init__(
        self,
        projects: ProjectRepository,
        boards: BoardRepository,
        items: WorkItemRepository,
        sprints: SprintRepository,
        assignments: AssignmentRepository,
        clock: Clock,
    ) -> None:
        self._projects = projects
        self._boards = boards
        self._items = items
        self._sprints = sprints
        self._assignments = assignments
        self._clock = clock

    async def execute(
        self,
        *,
        workspace_id: uuid.UUID,
        item_id: uuid.UUID,
        sprint_id: uuid.UUID | None,
    ) -> WorkItemView:
        item = await self._items.get(item_id)
        if item is None:
            raise NotFoundError("Item não encontrado", code="ITEM_NOT_FOUND")
        _, board = await _load_context(
            projects=self._projects,
            boards=self._boards,
            workspace_id=workspace_id,
            project_id=item.project_id,
        )
        now = self._clock.now()
        if sprint_id is not None:
            sprint = await self._sprints.get(sprint_id)
            if sprint is None or sprint.board_id != board.id:
                raise NotFoundError("Sprint não encontrada", code="SPRINT_NOT_FOUND")
            if sprint.state is SprintState.COMPLETED:
                raise ConflictError("Sprint concluída não aceita itens", code="SPRINT_COMPLETED")
        await self._assignments.close_open_for_item(item.id, now)
        if sprint_id is not None:
            await self._assignments.add(
                AssignmentRecord(
                    id=uuid7(),
                    work_item_id=item.id,
                    sprint_id=sprint_id,
                    added_at=now,
                    removed_at=None,
                )
            )
        item.assign_sprint(sprint_id, now=now)
        item.version += 1
        await self._items.save(item)
        return item_view(item, board)


class CreateSprint:
    def __init__(
        self,
        projects: ProjectRepository,
        boards: BoardRepository,
        sprints: SprintRepository,
        clock: Clock,
    ) -> None:
        self._projects = projects
        self._boards = boards
        self._sprints = sprints
        self._clock = clock

    async def execute(
        self,
        *,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        name: str,
        goal: str | None,
        start_date: date,
        end_date: date,
    ) -> SprintView:
        _, board = await _load_context(
            projects=self._projects,
            boards=self._boards,
            workspace_id=workspace_id,
            project_id=project_id,
        )
        sprint = Sprint.create(
            board_id=board.id,
            name=name,
            goal=goal,
            start_date=start_date,
            end_date=end_date,
            now=self._clock.now(),
        )
        await self._sprints.add(sprint)
        return sprint_view(sprint, [])


class StartSprint:
    def __init__(
        self,
        projects: ProjectRepository,
        boards: BoardRepository,
        items: WorkItemRepository,
        sprints: SprintRepository,
        clock: Clock,
    ) -> None:
        self._projects = projects
        self._boards = boards
        self._items = items
        self._sprints = sprints
        self._clock = clock

    async def execute(self, *, workspace_id: uuid.UUID, sprint_id: uuid.UUID) -> SprintView:
        sprint = await self._sprints.get(sprint_id)
        if sprint is None:
            raise NotFoundError("Sprint não encontrada", code="SPRINT_NOT_FOUND")
        board = await self._boards.get(sprint.board_id)
        if board is None:
            raise NotFoundError("Board não encontrado", code="BOARD_NOT_FOUND")
        if await self._projects.get(board.project_id, workspace_id) is None:
            raise NotFoundError("Sprint não encontrada", code="SPRINT_NOT_FOUND")
        active = await self._sprints.active_for_board(board.id)
        if active is not None and active.id != sprint.id:
            raise ConflictError(
                f"Já existe sprint ativa neste board: {active.name}",
                code="SPRINT_ALREADY_ACTIVE",
            )
        assigned = await self._sprints.count_assigned(sprint.id)
        sprint.start(assigned_items=assigned)
        await self._sprints.save(sprint)
        items = await self._items.list_for_sprint(sprint.id)
        return sprint_view(sprint, items)


class CompleteSprint:
    def __init__(
        self,
        projects: ProjectRepository,
        boards: BoardRepository,
        items: WorkItemRepository,
        sprints: SprintRepository,
        assignments: AssignmentRepository,
        clock: Clock,
    ) -> None:
        self._projects = projects
        self._boards = boards
        self._items = items
        self._sprints = sprints
        self._assignments = assignments
        self._clock = clock

    async def execute(
        self,
        *,
        workspace_id: uuid.UUID,
        sprint_id: uuid.UUID,
        target_sprint_id: uuid.UUID | None = None,
    ) -> SprintView:
        sprint = await self._sprints.get(sprint_id)
        if sprint is None:
            raise NotFoundError("Sprint não encontrada", code="SPRINT_NOT_FOUND")
        board = await self._boards.get(sprint.board_id)
        if board is None:
            raise NotFoundError("Board não encontrado", code="BOARD_NOT_FOUND")
        if await self._projects.get(board.project_id, workspace_id) is None:
            raise NotFoundError("Sprint não encontrada", code="SPRINT_NOT_FOUND")

        now = self._clock.now()
        items = await self._items.list_for_sprint(sprint.id)
        open_items = [item for item in items if item.done_at is None]
        if target_sprint_id is not None and open_items:
            target = await self._sprints.get(target_sprint_id)
            if target is None or target.board_id != sprint.board_id or target.id == sprint.id:
                raise NotFoundError("Sprint destino não encontrada", code="SPRINT_NOT_FOUND")
            if target.state is SprintState.COMPLETED:
                raise ConflictError("Sprint destino já concluída", code="SPRINT_COMPLETED")
        for item in open_items:
            await self._assignments.close_open_for_item(item.id, now)
            if target_sprint_id is not None:
                await self._assignments.add(
                    AssignmentRecord(
                        id=uuid7(),
                        work_item_id=item.id,
                        sprint_id=target_sprint_id,
                        added_at=now,
                        removed_at=None,
                    )
                )
            item.assign_sprint(target_sprint_id, now=now)
            item.version += 1
        if open_items:
            await self._items.save_many(open_items)
        sprint.complete(now=now)
        await self._sprints.save(sprint)
        return sprint_view(sprint, items)


class GetSprint:
    def __init__(
        self,
        projects: ProjectRepository,
        boards: BoardRepository,
        items: WorkItemRepository,
        sprints: SprintRepository,
    ) -> None:
        self._projects = projects
        self._boards = boards
        self._items = items
        self._sprints = sprints

    async def execute(self, *, workspace_id: uuid.UUID, sprint_id: uuid.UUID) -> SprintView:
        sprint = await self._sprints.get(sprint_id)
        if sprint is None:
            raise NotFoundError("Sprint não encontrada", code="SPRINT_NOT_FOUND")
        board = await self._boards.get(sprint.board_id)
        if board is None or await self._projects.get(board.project_id, workspace_id) is None:
            raise NotFoundError("Sprint não encontrada", code="SPRINT_NOT_FOUND")
        items = await self._items.list_for_sprint(sprint.id)
        return sprint_view(sprint, items)


class ListSprints:
    def __init__(
        self,
        projects: ProjectRepository,
        items: WorkItemRepository,
        sprints: SprintRepository,
    ) -> None:
        self._projects = projects
        self._items = items
        self._sprints = sprints

    async def execute(self, *, workspace_id: uuid.UUID, project_id: uuid.UUID) -> list[SprintView]:
        project = await self._projects.get(project_id, workspace_id)
        if project is None:
            raise NotFoundError("Projeto não encontrado", code="PROJECT_NOT_FOUND")
        sprints = await self._sprints.list_for_project(project.id)
        views: list[SprintView] = []
        for sprint in sprints:
            items = await self._items.list_for_sprint(sprint.id)
            views.append(sprint_view(sprint, items))
        return views
