"""Objetos de valor do contexto work."""

from __future__ import annotations

import re
from enum import StrEnum

from cadencia.shared.errors import ValidationError

FIBONACCI_POINTS: frozenset[int] = frozenset({1, 2, 3, 5, 8, 13})
PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")


class WorkItemType(StrEnum):
    EPIC = "EPIC"
    STORY = "STORY"
    TASK = "TASK"
    BUG = "BUG"
    SUBTASK = "SUBTASK"


class StatusCategory(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class SprintState(StrEnum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class Priority(StrEnum):
    LOWEST = "LOWEST"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    HIGHEST = "HIGHEST"


class ProjectMode(StrEnum):
    POINTS = "POINTS"
    COUNT = "COUNT"


class WipEnforcement(StrEnum):
    SOFT = "SOFT"
    HARD = "HARD"


DEFAULT_COLUMNS: tuple[tuple[str, StatusCategory, int | None], ...] = (
    ("To Do", StatusCategory.TODO, None),
    ("In Progress", StatusCategory.IN_PROGRESS, None),
    ("Done", StatusCategory.DONE, None),
)

PARENT_ALLOWED: dict[WorkItemType, frozenset[WorkItemType]] = {
    WorkItemType.STORY: frozenset({WorkItemType.EPIC}),
    WorkItemType.TASK: frozenset({WorkItemType.EPIC, WorkItemType.STORY}),
    WorkItemType.BUG: frozenset({WorkItemType.EPIC, WorkItemType.STORY}),
    WorkItemType.SUBTASK: frozenset({WorkItemType.STORY, WorkItemType.TASK, WorkItemType.BUG}),
}


def normalize_project_key(raw: str) -> str:
    key = raw.strip().upper()
    if not PROJECT_KEY_RE.match(key):
        raise ValidationError(
            "Chave do projeto deve ter 2 a 10 caracteres: letra seguida de letras/números",
            code="INVALID_PROJECT_KEY",
        )
    return key


def validate_story_points(value: int | None) -> int | None:
    if value is None:
        return None
    if value not in FIBONACCI_POINTS:
        raise ValidationError(
            "Story points devem seguir a sequência de Fibonacci 1,2,3,5,8,13",
            code="INVALID_STORY_POINTS",
        )
    return value


def validate_title(value: str) -> str:
    title = value.strip()
    if not title or len(title) > 200:
        raise ValidationError("Título deve ter de 1 a 200 caracteres", code="INVALID_TITLE")
    return title
