"""Porta de leitura de métricas — implementada na infraestrutura sobre o event log."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

from cadencia.metrics.domain.models import FlowSnapshot, SprintMetricsData


class MetricsReader(Protocol):
    async def sprint_data(
        self, *, workspace_id: uuid.UUID, sprint_id: uuid.UUID
    ) -> SprintMetricsData | None: ...

    async def project_sprints_data(
        self, *, workspace_id: uuid.UUID, project_id: uuid.UUID, last: int | None = None
    ) -> list[SprintMetricsData] | None: ...

    async def flow_items(
        self,
        *,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        since: datetime,
        until: datetime,
    ) -> list[FlowSnapshot] | None: ...
