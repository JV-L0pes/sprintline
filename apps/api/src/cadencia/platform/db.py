"""Engine/sessão SQLAlchemy async. Postgres em produção, SQLite em dev/testes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import sqlalchemy as sa
from fastapi import Request
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool

from cadencia.platform.config import Settings
from cadencia.shared.ids import uuid7

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

JSONVariant = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


class Base(DeclarativeBase):
    metadata = sa.MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), default=None)


def normalize_database_url(url: str) -> str:
    """Traduz parametros libpq para o que o asyncpg entende.

    URLs do Neon vem com `?sslmode=require` (padrão libpq); o dialeto asyncpg
    espera `ssl=require`. `channel_binding` também e ignorado.
    """
    if not url.startswith("postgresql+asyncpg"):
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    if "sslmode" in query:
        query["ssl"] = query.pop("sslmode")
    query.pop("channel_binding", None)
    return urlunsplit(parts._replace(query=urlencode(query)))


def build_engine(settings: Settings) -> AsyncEngine:
    url = normalize_database_url(settings.database_url)
    if url.startswith("sqlite"):
        return create_async_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=NullPool if ":memory:" not in url else sa.pool.StaticPool,
        )
    # Postgres serverless (Neon/pgbouncer): sem pool local, sem prepared statements.
    return create_async_engine(
        url,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
        pool_pre_ping=True,
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Unit of Work por request: commit no sucesso, rollback em qualquer erro."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def utcnow() -> datetime:
    return datetime.now(UTC)


def ensure_utc(moment: datetime | None) -> datetime | None:
    """SQLite perde tzinfo; normalizamos tudo para UTC aware na leitura."""
    if moment is None:
        return None
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)


__all__ = [
    "Base",
    "JSONVariant",
    "TimestampMixin",
    "build_engine",
    "build_session_factory",
    "get_session",
    "utcnow",
    "uuid7",
]
