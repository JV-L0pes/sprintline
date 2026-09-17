"""Politicas puras do contexto work (regras RN-06..RN-18)."""

from __future__ import annotations

from cadencia.shared.errors import ValidationError
from cadencia.work.domain.value_objects import (
    PARENT_ALLOWED,
    Priority,
    StatusCategory,
    WorkItemType,
)


def ensure_hierarchy_child(child_type: WorkItemType, parent_type: WorkItemType) -> None:
    """RN-09: EPIC não tem pai; SUBTASK exige pai válido; profundidade máxima 2."""
    if child_type is WorkItemType.EPIC:
        raise ValidationError("Epic não pode ser filho de outro item", code="EPIC_WITH_PARENT")
    allowed = PARENT_ALLOWED.get(child_type, frozenset())
    if parent_type not in allowed:
        raise ValidationError(
            f"{child_type.value} não pode ser filho de {parent_type.value}",
            code="INVALID_HIERARCHY",
        )


def ensure_points_allowed(item_type: WorkItemType, points: int | None) -> None:
    """RN-10: subtasks não carregam pontos (contagem acontece no item pai)."""
    if points is not None and item_type is WorkItemType.SUBTASK:
        raise ValidationError(
            "Subtasks não possuem story points; a estimativa fica no item pai",
            code="SUBTASK_POINTS_NOT_ALLOWED",
        )


class WipVerdict:
    OK = "OK"
    WARN = "WARN"
    BLOCK = "BLOCK"


def wip_verdict(
    *,
    wip_limit: int | None,
    current_count: int,
    enforcement: str,
) -> str:
    """RN-13: exceder WIP gera alerta (SOFT) ou bloqueio (HARD)."""
    if wip_limit is None or current_count < wip_limit:
        return WipVerdict.OK
    return WipVerdict.BLOCK if enforcement == "HARD" else WipVerdict.WARN


def ensure_sprint_can_start(*, goal: str | None, assigned_items: int) -> None:
    """RN-16: iniciar sprint exige objetivo e ao menos 1 item."""
    if not goal or not goal.strip():
        raise ValidationError("Sprint precisa de um objetivo (goal)", code="SPRINT_GOAL_REQUIRED")
    if assigned_items < 1:
        raise ValidationError(
            "Sprint precisa de ao menos 1 item no Sprint Backlog", code="SPRINT_EMPTY"
        )


def ensure_priority(value: str) -> Priority:
    try:
        return Priority(value)
    except ValueError as exc:
        raise ValidationError(f"Prioridade inválida: {value}", code="INVALID_PRIORITY") from exc


def next_category_is_done(category: StatusCategory) -> bool:
    return category is StatusCategory.DONE
