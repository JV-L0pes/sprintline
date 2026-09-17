"""Erros de dominio — carregam código estavel de negocio (RFC 9457 no transporte)."""

from __future__ import annotations

from typing import ClassVar


class DomainError(Exception):
    """Erro de negocio. `code` e estavel e traduzido no cliente."""

    default_code: ClassVar[str] = "DOMAIN_ERROR"
    http_status: ClassVar[int] = 422

    def __init__(self, detail: str, *, code: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code or self.default_code


class ValidationError(DomainError):
    default_code: ClassVar[str] = "VALIDATION_ERROR"
    http_status: ClassVar[int] = 422


class NotFoundError(DomainError):
    default_code: ClassVar[str] = "NOT_FOUND"
    http_status: ClassVar[int] = 404


class ConflictError(DomainError):
    default_code: ClassVar[str] = "CONFLICT"
    http_status: ClassVar[int] = 409


class UnauthorizedError(DomainError):
    default_code: ClassVar[str] = "UNAUTHORIZED"
    http_status: ClassVar[int] = 401


class ForbiddenError(DomainError):
    default_code: ClassVar[str] = "FORBIDDEN"
    http_status: ClassVar[int] = 403


class RateLimitError(DomainError):
    default_code: ClassVar[str] = "RATE_LIMITED"
    http_status: ClassVar[int] = 429

    def __init__(self, detail: str, *, retry_after_seconds: int, code: str | None = None) -> None:
        super().__init__(detail, code=code)
        self.retry_after_seconds = retry_after_seconds
