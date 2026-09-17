"""Calculadoras puras das métricas ágeis (spec RM-01..RM-15).

Sem I/O, sem relogio global: tudo entra por parametro — o que torna cada
invariante testável com property-based testing.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from cadencia.metrics.domain.models import (
    BurndownSeries,
    BurndownTotals,
    CfdDay,
    CfdSeries,
    DayPoint,
    FlowSnapshot,
    FlowTimes,
    ItemFlow,
    ScopeChange,
    SprintMetricsData,
    SprintRef,
    VelocityPoint,
    VelocityReport,
)
from cadencia.work.domain.value_objects import ProjectMode, StatusCategory


def working_days_between(start: date, end: date, working_days: tuple[int, ...]) -> list[date]:
    """RM-01: dias úteis do workspace no intervalo (inclusivo)."""
    days: list[date] = []
    current = start
    while current <= end:
        if current.weekday() in working_days:
            days.append(current)
        current += timedelta(days=1)
    if not days:
        return [start]
    return days


def end_of_day(moment_date: date, timezone: str) -> datetime:
    """Instante (UTC) do fim do dia local do workspace."""
    zone = ZoneInfo(timezone)
    local_end = datetime.combine(
        moment_date, time(hour=23, minute=59, second=59, microsecond=999999)
    )
    return local_end.replace(tzinfo=zone).astimezone(UTC)


def _in_scope_weight(items: list[ItemFlow], moment: datetime, mode: ProjectMode) -> float:
    return sum(item.weight(mode) for item in items if item.in_scope_at(moment))


def _completed_weight(items: list[ItemFlow], moment: datetime, mode: ProjectMode) -> float:
    return sum(
        item.weight(mode)
        for item in items
        if item.in_scope_at(moment) and item.category_at(moment) is StatusCategory.DONE
    )


def _scope_changes(
    items: list[ItemFlow],
    *,
    start_date: date,
    end_date: date,
    timezone: str,
    mode: ProjectMode,
) -> list[ScopeChange]:
    zone = ZoneInfo(timezone)
    changes: list[ScopeChange] = []
    for item in items:
        weight = item.weight(mode)
        if weight == 0:
            continue
        for window in item.windows:
            added_date = window.added_at.astimezone(zone).date()
            if start_date < added_date <= end_date:
                changes.append(ScopeChange(date=added_date, delta=weight, kind="added"))
            if window.removed_at is not None:
                removed_date = window.removed_at.astimezone(zone).date()
                if start_date < removed_date <= end_date:
                    changes.append(ScopeChange(date=removed_date, delta=-weight, kind="removed"))
    changes.sort(key=lambda change: change.date)
    return changes


def build_burndown(
    data: SprintMetricsData,
) -> BurndownSeries:
    """RM-02..RM-06: serie diaria de escopo, concluído, restante e ideal."""
    sprint: SprintRef = data.sprint
    mode = sprint.mode
    days = working_days_between(sprint.start_date, sprint.end_date, sprint.working_days)

    initial_scope = _in_scope_weight(data.items, end_of_day(days[0], sprint.timezone), mode)
    total_days = len(days)
    points: list[DayPoint] = []
    last_completed = 0.0
    last_scope = initial_scope
    for index, day in enumerate(days):
        moment = end_of_day(day, sprint.timezone)
        scope = _in_scope_weight(data.items, moment, mode)
        completed = _completed_weight(data.items, moment, mode)
        remaining = max(0.0, scope - completed)
        ideal = initial_scope * (1 - index / (total_days - 1)) if total_days > 1 else 0.0
        points.append(
            DayPoint(
                date=day,
                index=index,
                ideal=round(ideal, 4),
                remaining=round(remaining, 4),
                completed=round(completed, 4),
                scope=round(scope, 4),
            )
        )
        last_completed = completed
        last_scope = scope

    unestimated = (
        sum(1 for item in data.items if not item.is_subtask and item.story_points is None)
        if mode is ProjectMode.POINTS
        else 0
    )
    return BurndownSeries(
        sprint_id=sprint.id,
        sprint_name=sprint.name,
        unit="points" if mode is ProjectMode.POINTS else "items",
        start_date=sprint.start_date,
        end_date=sprint.end_date,
        days=points,
        scope_changes=_scope_changes(
            data.items,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            timezone=sprint.timezone,
            mode=mode,
        ),
        totals=BurndownTotals(
            initial_scope=round(initial_scope, 4),
            final_scope=round(last_scope, 4),
            completed=round(last_completed, 4),
            unestimated_items=unestimated,
        ),
    )


def build_velocity(series: list[BurndownSeries], *, average_window: int = 3) -> VelocityReport:
    """RM-08: velocity por sprint + média móvel das últimas N sprints."""
    points: list[VelocityPoint] = []
    for burndown in series:
        added = sum(change.delta for change in burndown.scope_changes if change.delta > 0)
        removed = sum(-change.delta for change in burndown.scope_changes if change.delta < 0)
        points.append(
            VelocityPoint(
                sprint_id=burndown.sprint_id,
                name=burndown.sprint_name,
                start_date=burndown.start_date,
                end_date=burndown.end_date,
                committed=burndown.totals.initial_scope,
                completed=burndown.totals.completed,
                added=round(added, 4),
                removed=round(removed, 4),
            )
        )
    window = points[-average_window:] if average_window > 0 else []
    average = round(sum(point.completed for point in window) / len(window), 2) if window else 0.0
    unit = series[-1].unit if series else "points"
    return VelocityReport(unit=unit, sprints=points, average=average)


def build_cfd(
    *,
    sprint_id: uuid.UUID,
    start_date: date,
    end_date: date,
    working_days: tuple[int, ...],
    timezone: str,
    items: list[ItemFlow],
) -> CfdSeries:
    """RM-11: contagem de itens por categoria ao fim de cada dia útil."""
    days = working_days_between(start_date, end_date, working_days)
    series: list[CfdDay] = []
    categories = [category.value for category in StatusCategory]
    for day in days:
        moment = end_of_day(day, timezone)
        counts = dict.fromkeys(categories, 0)
        for item in items:
            category = item.category_at(moment)
            if category is not None:
                counts[category.value] += 1
        series.append(CfdDay(date=day, counts=counts))
    return CfdSeries(sprint_id=sprint_id, start_date=start_date, end_date=end_date, days=series)


def percentile(values: list[float], fraction: float) -> float | None:
    """Percentil com interpolação linear (a convenção de flow metrics)."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = fraction * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 2)


def build_flow_times(items: list[FlowSnapshot]) -> FlowTimes:
    """RM-10: cycle time (in progress -> done) e lead time (created -> done)."""
    cycle_values = [
        (item.done_at - item.first_in_progress_at).total_seconds() / 86400
        for item in items
        if item.first_in_progress_at is not None
    ]
    lead_values = [(item.done_at - item.created_at).total_seconds() / 86400 for item in items]
    return FlowTimes(
        count=len(items),
        unit="days",
        cycle_p50=percentile(cycle_values, 0.50),
        cycle_p85=percentile(cycle_values, 0.85),
        cycle_p95=percentile(cycle_values, 0.95),
        lead_p50=percentile(lead_values, 0.50),
        lead_p85=percentile(lead_values, 0.85),
        lead_p95=percentile(lead_values, 0.95),
    )
