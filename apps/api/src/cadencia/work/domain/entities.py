"""Agregados do contexto work: Project, Board, WorkItem, Sprint."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from cadencia.shared.domain import AggregateRoot, DomainEvent
from cadencia.shared.errors import ConflictError, ValidationError
from cadencia.shared.ids import uuid7
from cadencia.work.domain.policies import (
    ensure_hierarchy_child,
    ensure_points_allowed,
    ensure_sprint_can_start,
)
from cadencia.work.domain.value_objects import (
    DEFAULT_COLUMNS,
    Priority,
    ProjectMode,
    SprintState,
    StatusCategory,
    WipEnforcement,
    WorkItemType,
    normalize_project_key,
    validate_story_points,
    validate_title,
)

SPRINT_MIN_DAYS = 7
SPRINT_MAX_DAYS = 28


# ---------------------------------------------------------------- Project ---
@dataclass(frozen=True)
class ProjectCreated(DomainEvent):
    event_type = "project.created"
    name: str
    key: str
    mode: str


class Project(AggregateRoot):
    def __init__(
        self,
        *,
        workspace_id: uuid.UUID,
        name: str,
        key: str,
        mode: ProjectMode = ProjectMode.POINTS,
        wip_enforcement: WipEnforcement = WipEnforcement.SOFT,
        next_number: int = 1,
        created_at: datetime,
        archived_at: datetime | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(entity_id)
        if not name.strip():
            raise ValidationError("Nome do projeto e obrigatorio", code="INVALID_NAME")
        self.workspace_id = workspace_id
        self.name = name.strip()[:120]
        self.key = key
        self.mode = mode
        self.wip_enforcement = wip_enforcement
        self.next_number = next_number
        self.created_at = created_at
        self.archived_at = archived_at

    @classmethod
    def create(
        cls,
        *,
        workspace_id: uuid.UUID,
        name: str,
        key: str,
        mode: ProjectMode,
        wip_enforcement: WipEnforcement,
        now: datetime,
    ) -> Project:
        project = cls(
            workspace_id=workspace_id,
            name=name,
            key=normalize_project_key(key),
            mode=mode,
            wip_enforcement=wip_enforcement,
            created_at=now,
        )
        project._record(ProjectCreated(name=project.name, key=project.key, mode=project.mode.value))
        return project

    def allocate_item_number(self) -> int:
        number = self.next_number
        self.next_number += 1
        return number


# ------------------------------------------------------------------ Board ---
class BoardColumn(AggregateRoot):
    def __init__(
        self,
        *,
        board_id: uuid.UUID,
        name: str,
        position: int,
        category: StatusCategory,
        wip_limit: int | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.board_id = board_id
        self.name = name.strip()[:60]
        self.position = position
        self.category = category
        self.wip_limit = wip_limit


class Board(AggregateRoot):
    def __init__(
        self,
        *,
        project_id: uuid.UUID,
        name: str,
        columns: list[BoardColumn],
        entity_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.project_id = project_id
        self.name = name.strip()[:120]
        self.columns = columns

    @classmethod
    def with_default_columns(cls, *, project_id: uuid.UUID, name: str) -> Board:
        board_id = uuid7()
        columns = [
            BoardColumn(
                board_id=board_id,
                name=column_name,
                position=index,
                category=category,
                wip_limit=wip_limit,
            )
            for index, (column_name, category, wip_limit) in enumerate(DEFAULT_COLUMNS)
        ]
        return cls(entity_id=board_id, project_id=project_id, name=name, columns=columns)

    def column(self, column_id: uuid.UUID) -> BoardColumn | None:
        return next((column for column in self.columns if column.id == column_id), None)

    def _reindex(self) -> None:
        for position, column in enumerate(sorted(self.columns, key=lambda column: column.position)):
            column.position = position

    def ensure_category_coverage(self) -> None:
        """RN-06: o board precisa de pelo menos uma coluna por categoria."""
        for category in StatusCategory:
            if not any(column.category is category for column in self.columns):
                raise ValidationError(
                    f"O board precisa de pelo menos uma coluna de {category.value}",
                    code="BOARD_MISSING_CATEGORY",
                )

    def add_column(
        self,
        *,
        name: str,
        category: StatusCategory,
        wip_limit: int | None = None,
        position: int | None = None,
    ) -> BoardColumn:
        if not name.strip():
            raise ValidationError("Nome da coluna e obrigatorio", code="INVALID_COLUMN_NAME")
        if wip_limit is not None and wip_limit < 1:
            raise ValidationError("WIP limit deve ser >= 1", code="INVALID_WIP_LIMIT")
        column = BoardColumn(
            board_id=self.id,
            name=name,
            position=position if position is not None else len(self.columns),
            category=category,
            wip_limit=wip_limit,
        )
        self.columns.append(column)
        self._reindex()
        return column

    def update_column(
        self,
        column_id: uuid.UUID,
        *,
        name: str | None = None,
        wip_limit: int | None = None,
        clear_wip: bool = False,
    ) -> BoardColumn:
        column = self.column(column_id)
        if column is None:
            raise ValidationError("Coluna nao encontrada", code="COLUMN_NOT_FOUND")
        if name is not None:
            if not name.strip():
                raise ValidationError("Nome da coluna e obrigatorio", code="INVALID_COLUMN_NAME")
            column.name = name.strip()[:60]
        if clear_wip:
            column.wip_limit = None
        elif wip_limit is not None:
            if wip_limit < 1:
                raise ValidationError("WIP limit deve ser >= 1", code="INVALID_WIP_LIMIT")
            column.wip_limit = wip_limit
        return column

    def remove_column(self, column_id: uuid.UUID) -> None:
        column = self.column(column_id)
        if column is None:
            raise ValidationError("Coluna nao encontrada", code="COLUMN_NOT_FOUND")
        remaining = [candidate for candidate in self.columns if candidate.id != column_id]
        if not any(candidate.category is column.category for candidate in remaining):
            raise ValidationError(
                "Nao e possivel remover a ultima coluna desta categoria",
                code="BOARD_LAST_CATEGORY_COLUMN",
            )
        self.columns = remaining
        self._reindex()

    def reorder_columns(self, column_ids: list[uuid.UUID]) -> None:
        if {column.id for column in self.columns} != set(column_ids):
            raise ValidationError(
                "A ordenacao deve conter exatamente as colunas do board",
                code="INVALID_COLUMN_ORDER",
            )
        by_id = {column.id: column for column in self.columns}
        for position, column_id in enumerate(column_ids):
            by_id[column_id].position = position

    def first_todo_column(self) -> BoardColumn:
        todo = [column for column in self.columns if column.category is StatusCategory.TODO]
        if not todo:
            raise ValidationError("Board sem coluna de categoria TODO", code="BOARD_MISSING_TODO")
        return sorted(todo, key=lambda column: column.position)[0]


# -------------------------------------------------------------- WorkItem ---
@dataclass(frozen=True)
class WorkItemCreated(DomainEvent):
    event_type = "work_item.created"
    project_id: str
    key: str
    type: str
    title: str
    story_points: int | None
    status_category: str
    sprint_id: str | None


@dataclass(frozen=True)
class WorkItemUpdated(DomainEvent):
    event_type = "work_item.updated"
    fields: tuple[str, ...]


@dataclass(frozen=True)
class WorkItemMoved(DomainEvent):
    event_type = "work_item.moved"
    from_column_id: str | None
    to_column_id: str
    from_category: str | None
    to_category: str


@dataclass(frozen=True)
class WorkItemCompleted(DomainEvent):
    event_type = "work_item.completed"
    story_points: int | None
    sprint_id: str | None


@dataclass(frozen=True)
class WorkItemReopened(DomainEvent):
    event_type = "work_item.reopened"
    story_points: int | None
    sprint_id: str | None


@dataclass(frozen=True)
class WorkItemSprintChanged(DomainEvent):
    event_type = "work_item.sprint_changed"
    from_sprint_id: str | None
    to_sprint_id: str | None


@dataclass(frozen=True)
class WorkItemArchived(DomainEvent):
    event_type = "work_item.archived"


class WorkItem(AggregateRoot):
    def __init__(
        self,
        *,
        project_id: uuid.UUID,
        key: str,
        type: WorkItemType,
        title: str,
        status_column_id: uuid.UUID,
        created_at: datetime,
        parent_id: uuid.UUID | None = None,
        description: str = "",
        story_points: int | None = None,
        priority: Priority = Priority.MEDIUM,
        assignee_id: uuid.UUID | None = None,
        sprint_id: uuid.UUID | None = None,
        position: float = 0.0,
        due_date: date | None = None,
        done_at: datetime | None = None,
        first_in_progress_at: datetime | None = None,
        updated_at: datetime | None = None,
        archived_at: datetime | None = None,
        version: int = 1,
        entity_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.project_id = project_id
        self.parent_id = parent_id
        self.key = key
        self.type = type
        self.title = title
        self.description = description
        self.status_column_id = status_column_id
        self.story_points = story_points
        self.priority = priority
        self.assignee_id = assignee_id
        self.sprint_id = sprint_id
        self.position = position
        self.due_date = due_date
        self.created_at = created_at
        self.updated_at = updated_at
        self.done_at = done_at
        self.first_in_progress_at = first_in_progress_at
        self.archived_at = archived_at
        self.version = version

    @classmethod
    def create(
        cls,
        *,
        project: Project,
        item_type: WorkItemType,
        title: str,
        todo_column_id: uuid.UUID,
        position: float,
        now: datetime,
        parent_id: uuid.UUID | None = None,
        parent_type: WorkItemType | None = None,
        description: str = "",
        story_points: int | None = None,
        priority: Priority = Priority.MEDIUM,
        assignee_id: uuid.UUID | None = None,
        due_date: date | None = None,
        key: str,
    ) -> WorkItem:
        if parent_id is not None:
            if parent_type is None:
                raise ValidationError("Item pai nao encontrado", code="PARENT_NOT_FOUND")
            ensure_hierarchy_child(item_type, parent_type)
        ensure_points_allowed(item_type, story_points)
        item = cls(
            project_id=project.id,
            key=key,
            type=item_type,
            title=validate_title(title),
            description=description,
            status_column_id=todo_column_id,
            story_points=validate_story_points(story_points),
            priority=priority,
            assignee_id=assignee_id,
            position=position,
            due_date=due_date,
            created_at=now,
            entity_id=None,
            parent_id=parent_id,
        )
        item._record(
            WorkItemCreated(
                project_id=str(project.id),
                key=key,
                type=item_type.value,
                title=item.title,
                story_points=item.story_points,
                status_category=StatusCategory.TODO.value,
                sprint_id=None,
            )
        )
        return item

    @property
    def is_done(self) -> bool:
        return self.done_at is not None

    def update_details(
        self,
        *,
        now: datetime,
        title: str | None = None,
        description: str | None = None,
        priority: Priority | None = None,
        assignee_id: uuid.UUID | None = None,
        clear_assignee: bool = False,
        story_points: int | None = None,
        clear_points: bool = False,
        due_date: date | None = None,
        clear_due_date: bool = False,
    ) -> None:
        changed: list[str] = []
        if title is not None:
            self.title = validate_title(title)
            changed.append("title")
        if description is not None:
            self.description = description
            changed.append("description")
        if priority is not None:
            self.priority = priority
            changed.append("priority")
        if clear_assignee:
            self.assignee_id = None
            changed.append("assignee_id")
        elif assignee_id is not None:
            self.assignee_id = assignee_id
            changed.append("assignee_id")
        if clear_points:
            self.story_points = None
            changed.append("story_points")
        elif story_points is not None:
            ensure_points_allowed(self.type, story_points)
            self.story_points = validate_story_points(story_points)
            changed.append("story_points")
        if clear_due_date:
            self.due_date = None
            changed.append("due_date")
        elif due_date is not None:
            self.due_date = due_date
            changed.append("due_date")
        if changed:
            self.updated_at = now
            self._record(WorkItemUpdated(fields=tuple(changed)))

    def move_to(self, *, column: BoardColumn, now: datetime) -> None:
        from_category = None
        if self.done_at is not None:
            from_category = StatusCategory.DONE.value
        elif self.first_in_progress_at is not None:
            from_category = StatusCategory.IN_PROGRESS.value
        else:
            from_category = StatusCategory.TODO.value

        self.status_column_id = column.id
        self.updated_at = now

        if column.category is StatusCategory.IN_PROGRESS and self.first_in_progress_at is None:
            self.first_in_progress_at = now
        if column.category is StatusCategory.DONE:
            if self.done_at is None:
                self.done_at = now
                self._record(
                    WorkItemCompleted(
                        story_points=self.story_points,
                        sprint_id=str(self.sprint_id) if self.sprint_id else None,
                    )
                )
        else:
            if self.done_at is not None:
                self.done_at = None
                self._record(
                    WorkItemReopened(
                        story_points=self.story_points,
                        sprint_id=str(self.sprint_id) if self.sprint_id else None,
                    )
                )

        self._record(
            WorkItemMoved(
                from_column_id=None,
                to_column_id=str(column.id),
                from_category=from_category,
                to_category=column.category.value,
            )
        )

    def assign_sprint(self, sprint_id: uuid.UUID | None, *, now: datetime) -> None:
        if self.sprint_id == sprint_id:
            return
        previous = self.sprint_id
        self.sprint_id = sprint_id
        self.updated_at = now
        self._record(
            WorkItemSprintChanged(
                from_sprint_id=str(previous) if previous else None,
                to_sprint_id=str(sprint_id) if sprint_id else None,
            )
        )

    def archive(self, *, now: datetime) -> None:
        if self.archived_at is not None:
            raise ConflictError("Item ja arquivado", code="ITEM_ALREADY_ARCHIVED")
        self.archived_at = now
        self.updated_at = now
        self._record(WorkItemArchived())


# ----------------------------------------------------------------- Sprint ---
@dataclass(frozen=True)
class SprintCreated(DomainEvent):
    event_type = "sprint.created"
    name: str
    goal: str | None
    start_date: str
    end_date: str


@dataclass(frozen=True)
class SprintStarted(DomainEvent):
    event_type = "sprint.started"
    name: str
    start_date: str
    end_date: str


@dataclass(frozen=True)
class SprintCompleted(DomainEvent):
    event_type = "sprint.completed"


class Sprint(AggregateRoot):
    def __init__(
        self,
        *,
        board_id: uuid.UUID,
        name: str,
        goal: str | None,
        state: SprintState,
        start_date: date,
        end_date: date,
        created_at: datetime,
        completed_at: datetime | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.board_id = board_id
        self.name = name.strip()[:120]
        self.goal = goal
        self.state = state
        self.start_date = start_date
        self.end_date = end_date
        self.completed_at = completed_at
        self.created_at = created_at

    @staticmethod
    def ensure_dates(start_date: date, end_date: date) -> None:
        duration = (end_date - start_date).days + 1
        if duration < SPRINT_MIN_DAYS or duration > SPRINT_MAX_DAYS:
            raise ValidationError(
                f"Sprint deve durar de {SPRINT_MIN_DAYS} a {SPRINT_MAX_DAYS} dias",
                code="INVALID_SPRINT_DURATION",
            )

    @classmethod
    def create(
        cls,
        *,
        board_id: uuid.UUID,
        name: str,
        goal: str | None,
        start_date: date,
        end_date: date,
        now: datetime,
    ) -> Sprint:
        cls.ensure_dates(start_date, end_date)
        sprint = cls(
            board_id=board_id,
            name=name,
            goal=goal,
            state=SprintState.PLANNED,
            start_date=start_date,
            end_date=end_date,
            created_at=now,
        )
        sprint._record(
            SprintCreated(
                name=sprint.name,
                goal=goal,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        )
        return sprint

    def update_plan(self, *, name: str | None, goal: str | None) -> None:
        if self.state is SprintState.COMPLETED:
            raise ConflictError("Sprint concluida e imutavel", code="SPRINT_COMPLETED")
        if name is not None:
            self.name = name.strip()[:120]
        if goal is not None:
            self.goal = goal

    def start(self, *, assigned_items: int) -> None:
        if self.state is not SprintState.PLANNED:
            raise ConflictError(
                f"Sprint em estado {self.state.value} nao pode ser iniciada",
                code="SPRINT_NOT_PLANNED",
            )
        ensure_sprint_can_start(goal=self.goal, assigned_items=assigned_items)
        self.state = SprintState.ACTIVE
        self._record(
            SprintStarted(
                name=self.name,
                start_date=self.start_date.isoformat(),
                end_date=self.end_date.isoformat(),
            )
        )

    def complete(self, *, now: datetime) -> None:
        if self.state is not SprintState.ACTIVE:
            raise ConflictError("Apenas sprint ativa pode ser concluida", code="SPRINT_NOT_ACTIVE")
        self.state = SprintState.COMPLETED
        self.completed_at = now
        self._record(SprintCompleted())
