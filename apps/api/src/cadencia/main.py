"""Application factory do Cadencia API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cadencia.identity.interface.router import router as identity_router
from cadencia.integrations.interface.router import router as integrations_router
from cadencia.metrics.interface.router import router as metrics_router
from cadencia.platform.config import Settings, get_settings
from cadencia.platform.db import Base, build_engine, build_session_factory
from cadencia.platform.errors import register_error_handlers
from cadencia.platform.logging import configure_logging
from cadencia.work.interface.router import router as work_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if settings.database_url.startswith("sqlite"):
            from cadencia.identity.infrastructure import orm as _identity_orm  # noqa: F401
            from cadencia.integrations.infrastructure import orm as _integrations_orm  # noqa: F401
            from cadencia.platform import orm as _platform_orm  # noqa: F401
            from cadencia.work.infrastructure import orm as _work_orm  # noqa: F401

            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
        yield
        await engine.dispose()

    app = FastAPI(
        title="Cadencia API",
        version="0.1.0",
        description="Kanban, sprints, metricas ageis e integracao Jira.",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(identity_router)
    app.include_router(work_router)
    app.include_router(metrics_router)
    app.include_router(integrations_router)

    @app.get("/healthz", tags=["platform"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
