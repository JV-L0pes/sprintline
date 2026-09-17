"""Adaptadores de segurança do contexto identity (portas da aplicação)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from cadencia.identity.application.ports import PasswordHasher, TokenIssuer
from cadencia.platform.config import Settings
from cadencia.platform.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)


class Argon2PasswordHasher(PasswordHasher):
    def hash(self, password: str) -> str:
        return hash_password(password)

    def verify(self, password_hash: str, password: str) -> bool:
        return verify_password(password_hash, password)


class JwtTokenIssuer(TokenIssuer):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_access(self, user_id: uuid.UUID, now: datetime) -> tuple[str, datetime]:
        return create_access_token(user_id=user_id, settings=self._settings, now=now)

    def generate_opaque_token(self) -> str:
        return generate_opaque_token()

    def hash_opaque_token(self, raw: str) -> str:
        return hash_opaque_token(raw)

    def refresh_ttl(self) -> timedelta:
        return timedelta(days=self._settings.refresh_token_ttl_days)
