"""View models do contexto integrations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IntegrationView:
    id: uuid.UUID
    provider: str
    site_url: str
    status: str
    story_points_field: str | None
    created_at: datetime


@dataclass(frozen=True)
class JiraFieldView:
    field_id: str
    name: str
    schema_type: str | None


@dataclass(frozen=True)
class FieldDiscoveryView:
    story_points_field: str | None
    fields: list[JiraFieldView]


@dataclass(frozen=True)
class TrelloBoardView:
    id: str
    name: str
    url: str
    closed: bool


@dataclass(frozen=True)
class SyncJobView:
    id: uuid.UUID
    job_type: str
    state: str
    project_key: str
    start_at: int
    imported_count: int
    last_error: str | None
    created_at: datetime
