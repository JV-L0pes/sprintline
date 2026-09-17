"""Mapeamento relacional do contexto work."""

from __future__ import annotations

import uuid
from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from cadencia.platform.db import Base


class ProjectRow(Base):
    __tablename__ = "projects"
    __table_args__ = (sa.UniqueConstraint("workspace_id", "key", name="uq_projects_workspace_key"),)

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(sa.String(120))
    key: Mapped[str] = mapped_column(sa.String(10))
    mode: Mapped[str] = mapped_column(sa.String(16), default="POINTS")
    wip_enforcement: Mapped[str] = mapped_column(sa.String(8), default="SOFT")
    next_number: Mapped[int] = mapped_column(sa.Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), default=None)


class BoardRow(Base):
    __tablename__ = "boards"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("projects.id", ondelete="CASCADE"), unique=True
    )
    name: Mapped[str] = mapped_column(sa.String(120))


class BoardColumnRow(Base):
    __tablename__ = "board_columns"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    board_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("boards.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(sa.String(60))
    position: Mapped[int] = mapped_column(sa.Integer)
    category: Mapped[str] = mapped_column(sa.String(16))
    wip_limit: Mapped[int | None] = mapped_column(sa.Integer, default=None)


class SprintRow(Base):
    __tablename__ = "sprints"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    board_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("boards.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(sa.String(120))
    goal: Mapped[str | None] = mapped_column(sa.Text, default=None)
    state: Mapped[str] = mapped_column(sa.String(16), default="PLANNED")
    start_date: Mapped[date] = mapped_column(sa.Date)
    end_date: Mapped[date] = mapped_column(sa.Date)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))


class WorkItemRow(Base):
    __tablename__ = "work_items"
    __table_args__ = (
        sa.UniqueConstraint("project_id", "key", name="uq_work_items_project_key"),
        sa.Index("ix_work_items_sprint", "sprint_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("work_items.id", ondelete="SET NULL"), default=None
    )
    sprint_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("sprints.id", ondelete="SET NULL"), default=None
    )
    type: Mapped[str] = mapped_column(sa.String(16))
    key: Mapped[str] = mapped_column(sa.String(24))
    title: Mapped[str] = mapped_column(sa.String(200))
    description: Mapped[str] = mapped_column(sa.Text, default="")
    status_column_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("board_columns.id", ondelete="RESTRICT")
    )
    story_points: Mapped[int | None] = mapped_column(sa.Integer, default=None)
    priority: Mapped[str] = mapped_column(sa.String(16), default="MEDIUM")
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    position: Mapped[float] = mapped_column(sa.Float, default=0.0)
    due_date: Mapped[date | None] = mapped_column(sa.Date, default=None)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), default=None)
    done_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), default=None)
    first_in_progress_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), default=None
    )
    archived_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), default=None)
    version: Mapped[int] = mapped_column(sa.Integer, default=1)


class SprintAssignmentRow(Base):
    __tablename__ = "sprint_assignments"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    work_item_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("work_items.id", ondelete="CASCADE"), index=True
    )
    sprint_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("sprints.id", ondelete="CASCADE"), index=True
    )
    added_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    removed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), default=None)
