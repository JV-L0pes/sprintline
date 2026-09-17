"""Testes das calculadoras de metricas: golden dataset + propriedades (RM-01..RM-15)."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cadencia.metrics.domain.calculators import (
    build_burndown,
    build_cfd,
    build_flow_times,
    build_velocity,
    percentile,
    working_days_between,
)
from cadencia.metrics.domain.models import (
    AssignmentWindow,
    FlowSnapshot,
    ItemFlow,
    ItemFlowEvent,
    SprintMetricsData,
    SprintRef,
)
from cadencia.work.domain.value_objects import ProjectMode, StatusCategory

SPRINT_ID = uuid.UUID("018f0000-0000-7000-8000-000000000001")
START = date(2026, 9, 7)  # segunda-feira
END = date(2026, 9, 18)  # sexta-feira
SPRINT = SprintRef(
    id=SPRINT_ID,
    project_id=uuid.uuid4(),
    board_id=uuid.uuid4(),
    name="Sprint 1",
    start_date=START,
    end_date=END,
    timezone="UTC",
    working_days=(0, 1, 2, 3, 4),
    mode=ProjectMode.POINTS,
)


def at(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 9, day, hour, 0, tzinfo=UTC)


def flow(
    *,
    points: int,
    added: datetime,
    events: list[tuple[datetime, StatusCategory]],
    windows: list[AssignmentWindow] | None = None,
) -> ItemFlow:
    return ItemFlow(
        id=uuid.uuid4(),
        key=f"APP-{points}",
        story_points=points,
        is_subtask=False,
        created_at=added,
        windows=tuple(windows or [AssignmentWindow(added_at=added, removed_at=None)]),
        category_events=tuple(
            ItemFlowEvent(occurred_at=moment, category=category) for moment, category in events
        ),
    )


def golden_items() -> list[ItemFlow]:
    item_a = flow(
        points=5,
        added=at(7, 9),
        events=[(at(7, 9), StatusCategory.TODO), (at(9), StatusCategory.DONE)],
    )
    item_b = flow(
        points=8,
        added=at(7, 9),
        events=[(at(7, 9), StatusCategory.TODO)],
    )
    item_c = flow(
        points=3,
        added=at(10, 10),
        events=[
            (at(10, 10), StatusCategory.TODO),
            (at(11), StatusCategory.DONE),
        ],
    )
    return [item_a, item_b, item_c]


def test_working_days_between_skips_weekends() -> None:
    days = working_days_between(START, END, (0, 1, 2, 3, 4))
    assert len(days) == 10
    assert days[0] == date(2026, 9, 7)
    assert days[-1] == date(2026, 9, 18)
    assert date(2026, 9, 12) not in days  # sabado


def test_burndown_golden_series() -> None:
    series = build_burndown(SprintMetricsData(sprint=SPRINT, items=golden_items()))

    remaining = [point.remaining for point in series.days]
    expected_remaining = [13, 13, 8, 11, 8, 8, 8, 8, 8, 8]
    for actual, expected in zip(remaining, expected_remaining, strict=True):
        assert actual == pytest.approx(expected)

    scope = [point.scope for point in series.days]
    expected_scope = [13] * 3 + [16] * 7
    for actual, expected in zip(scope, expected_scope, strict=True):
        assert actual == pytest.approx(expected)

    completed = [point.completed for point in series.days]
    expected_completed = [0, 0, 5, 5, 8, 8, 8, 8, 8, 8]
    for actual, expected in zip(completed, expected_completed, strict=True):
        assert actual == pytest.approx(expected)

    assert series.days[0].ideal == pytest.approx(13)
    assert series.days[-1].ideal == pytest.approx(0)
    assert series.days[3].ideal == pytest.approx(13 * (1 - 3 / 9), abs=1e-3)

    assert series.totals.initial_scope == pytest.approx(13)
    assert series.totals.final_scope == pytest.approx(16)
    assert series.totals.completed == pytest.approx(8)

    changes = series.scope_changes
    assert len(changes) == 1
    assert changes[0].date == date(2026, 9, 10)
    assert changes[0].delta == pytest.approx(3)
    assert changes[0].kind == "added"


def test_burndown_count_mode_ignores_points() -> None:
    count_sprint = replace(SPRINT, mode=ProjectMode.COUNT)
    series = build_burndown(SprintMetricsData(sprint=count_sprint, items=golden_items()))
    assert series.unit == "items"
    assert series.totals.initial_scope == pytest.approx(2)
    assert series.totals.final_scope == pytest.approx(3)


def test_burndown_reports_unestimated_items() -> None:
    unestimated = ItemFlow(
        id=uuid.uuid4(),
        key="APP-0",
        story_points=None,
        is_subtask=False,
        created_at=at(7, 9),
        windows=(AssignmentWindow(added_at=at(7, 9)),),
        category_events=(ItemFlowEvent(occurred_at=at(7, 9), category=StatusCategory.TODO),),
    )
    series = build_burndown(SprintMetricsData(sprint=SPRINT, items=[unestimated]))
    assert series.totals.unestimated_items == 1
    assert series.totals.initial_scope == pytest.approx(0)


def test_velocity_averages_last_three() -> None:
    data = SprintMetricsData(sprint=SPRINT, items=golden_items())
    series = build_burndown(data)
    report = build_velocity([series, series, series, series], average_window=3)
    assert len(report.sprints) == 4
    assert report.average == pytest.approx(8)
    point = report.sprints[-1]
    assert point.committed == pytest.approx(13)
    assert point.completed == pytest.approx(8)
    assert point.added == pytest.approx(3)


def test_cfd_counts_categories_per_day() -> None:
    cfd = build_cfd(
        sprint_id=SPRINT_ID,
        start_date=START,
        end_date=END,
        working_days=(0, 1, 2, 3, 4),
        timezone="UTC",
        items=golden_items(),
    )
    assert len(cfd.days) == 10
    assert cfd.days[0].counts["TODO"] == 2
    assert cfd.days[0].counts["DONE"] == 0
    assert cfd.days[-1].counts["DONE"] == 2
    assert cfd.days[-1].counts["TODO"] == 1


def test_flow_times_percentiles() -> None:
    items = [
        FlowSnapshot(key="A", created_at=at(7, 9), first_in_progress_at=at(8, 9), done_at=at(9, 9)),
        FlowSnapshot(
            key="B", created_at=at(7, 9), first_in_progress_at=at(8, 9), done_at=at(11, 9)
        ),
        FlowSnapshot(key="C", created_at=at(7, 9), first_in_progress_at=None, done_at=at(13, 9)),
    ]
    report = build_flow_times(items)
    assert report.count == 3
    assert report.lead_p50 == pytest.approx(4)
    assert report.cycle_p50 == pytest.approx(2)
    assert report.cycle_p95 == pytest.approx(2.9)
    assert report.lead_p95 == pytest.approx(5.8)


def test_percentile_edge_cases() -> None:
    assert percentile([], 0.5) is None
    assert percentile([4.0], 0.9) == 4.0


@settings(max_examples=75, deadline=None)
@given(
    points=st.lists(st.sampled_from([1, 2, 3, 5, 8, 13]), min_size=0, max_size=6),
    done_days=st.lists(st.integers(min_value=0, max_value=9), min_size=0, max_size=6),
)
def test_burndown_invariants(points: list[int], done_days: list[int]) -> None:
    """RM-04: restante nunca negativo; ideal nos extremos; concluido monotono."""
    items: list[ItemFlow] = []
    for index, point_value in enumerate(points):
        day = 7 + (done_days[index] if index < len(done_days) else 0) % 10
        category = StatusCategory.DONE if index < len(done_days) else StatusCategory.TODO
        events = [(at(7, 9), StatusCategory.TODO)]
        if category is StatusCategory.DONE:
            events.append((at(day, 12), StatusCategory.DONE))
        items.append(flow(points=point_value, added=at(7, 9), events=events))

    series = build_burndown(SprintMetricsData(sprint=SPRINT, items=items))
    assert all(point.remaining >= 0 for point in series.days)
    assert series.days[0].ideal == pytest.approx(series.totals.initial_scope)
    assert series.days[-1].ideal == pytest.approx(0)
    completed = [point.completed for point in series.days]
    assert completed == sorted(completed)
    scope_values = [point.scope for point in series.days]
    assert scope_values == sorted(scope_values)  # sem remocoes neste cenario


def test_timezone_boundary_uses_workspace_local_day() -> None:
    """RM-01: item concluido 22h em Sao Paulo conta no dia local, nao no UTC."""
    sprint = replace(SPRINT, timezone="America/Sao_Paulo")
    # 2026-09-08 22:00 BRT == 2026-09-09 01:00 UTC
    done_local = datetime(2026, 9, 9, 1, 0, tzinfo=UTC)
    item = ItemFlow(
        id=uuid.uuid4(),
        key="APP-1",
        story_points=5,
        is_subtask=False,
        created_at=datetime(2026, 9, 7, 9, 0, tzinfo=UTC),
        windows=(AssignmentWindow(added_at=datetime(2026, 9, 7, 9, 0, tzinfo=UTC)),),
        category_events=(
            ItemFlowEvent(
                occurred_at=datetime(2026, 9, 7, 9, 0, tzinfo=UTC), category=StatusCategory.TODO
            ),
            ItemFlowEvent(occurred_at=done_local, category=StatusCategory.DONE),
        ),
    )
    series = build_burndown(SprintMetricsData(sprint=sprint, items=[item]))
    # 22h BRT de 2026-09-08 ainda pertence ao dia local 08/09 (dia 1 da serie)
    assert series.days[1].completed == pytest.approx(5)
    assert series.days[0].completed == pytest.approx(0)


def test_zoneinfo_utc_end_of_day() -> None:
    zone = ZoneInfo("UTC")
    assert zone.utcoffset(datetime(2026, 9, 7)) is not None
