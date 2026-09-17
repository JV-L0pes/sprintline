"""Handlers HTTP que traduzem erros para RFC 9457 (application/problem+json)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from cadencia.shared.errors import DomainError, RateLimitError

logger = logging.getLogger("cadencia.errors")

PROBLEM_CONTENT_TYPE = "application/problem+json"


def problem(
    *,
    status: int,
    code: str,
    detail: str,
    title: str | None = None,
    instance: str | None = None,
    extra: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"https://docs.cadencia.dev/errors/{code.lower()}",
        "title": title or code.replace("_", " ").title(),
        "status": status,
        "detail": detail,
        "code": code,
    }
    if instance:
        body["instance"] = instance
    if extra:
        body["errors"] = extra
    return JSONResponse(
        status_code=status,
        content=body,
        media_type=PROBLEM_CONTENT_TYPE,
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        headers = None
        if isinstance(exc, RateLimitError):
            headers = {"Retry-After": str(exc.retry_after_seconds)}
        return problem(
            status=exc.http_status,
            code=exc.code,
            detail=exc.detail,
            instance=str(request.url.path),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return problem(
            status=422,
            code="REQUEST_VALIDATION_ERROR",
            detail="Corpo ou parametros da requisição inválidos",
            instance=str(request.url.path),
            extra={"fields": _sanitize(exc.errors())},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND"}.get(
            exc.status_code, f"HTTP_{exc.status_code}"
        )
        return problem(
            status=exc.status_code,
            code=code,
            detail=str(exc.detail),
            instance=str(request.url.path),
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erro inesperado em %s", request.url.path, exc_info=exc)
        return problem(
            status=500,
            code="INTERNAL_ERROR",
            detail="Erro interno inesperado",
            instance=str(request.url.path),
        )


def _sanitize(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized = []
    for error in errors:
        sanitized.append(
            {
                "loc": [str(part) for part in error.get("loc", [])],
                "msg": str(error.get("msg", "")),
                "type": str(error.get("type", "")),
            }
        )
    return sanitized
