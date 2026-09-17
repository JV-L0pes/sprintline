"""Schemas HTTP do contexto integrations."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IntegrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    site_url: str
    status: str
    story_points_field: str | None
    created_at: datetime


class AuthorizeOut(BaseModel):
    authorize_url: str


class JiraFieldOut(BaseModel):
    field_id: str
    name: str
    schema_type: str | None


class FieldDiscoveryOut(BaseModel):
    story_points_field: str | None
    fields: list[JiraFieldOut]


class ImportStartRequest(BaseModel):
    project_key: str = Field(min_length=1, max_length=20)


class TrelloConnectRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class TrelloBoardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    url: str
    closed: bool


class TrelloImportRequest(BaseModel):
    board_id: str = Field(min_length=1, max_length=64)


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_type: str
    state: str
    project_key: str
    start_at: int
    imported_count: int
    last_error: str | None
    created_at: datetime
