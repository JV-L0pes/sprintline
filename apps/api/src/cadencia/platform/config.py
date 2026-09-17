"""Configuracao 12-factor: tudo por variavel de ambiente (prefixo CADENCIA_)."""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CADENCIA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./cadencia.db"
    web_base_url: str = "http://localhost:5173"
    api_base_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:5173"

    jwt_secret: str = "cadencia-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "cadencia-api"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    cookie_name: str = "cadencia_refresh"
    cookie_secure: bool = False

    app_name: str = "Sprintline"
    # open | invite_only | closed — padrao seguro para uso privado
    registration_mode: str = "invite_only"
    login_max_attempts: int = 10
    login_window_minutes: int = 15
    register_max_attempts: int = 5
    register_window_minutes: int = 60
    refresh_max_attempts: int = 120
    refresh_window_minutes: int = 60

    @property
    def is_registration_open(self) -> bool:
        return self.registration_mode == "open"

    @property
    def is_registration_invite_only(self) -> bool:
        return self.registration_mode == "invite_only"

    integration_secret_key: str | None = None

    jira_client_id: str = ""
    jira_client_secret: str = ""
    jira_scopes: str = (
        "read:jira-work write:jira-work read:jira-user offline_access manage:jira-webhook"
    )

    trello_api_key: str = ""
    trello_app_name: str = "Cadencia"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def fernet_key(self) -> bytes:
        """Chave Fernet derivada: usa a chave dedicada se existir, senao deriva do jwt_secret."""
        if self.integration_secret_key:
            return self.integration_secret_key.encode()
        digest = hashlib.sha256(self.jwt_secret.encode()).digest()
        return base64.urlsafe_b64encode(digest)

    @property
    def jira_scope_list(self) -> list[str]:
        return [scope.strip() for scope in self.jira_scopes.split() if scope.strip()]

    @property
    def jira_redirect_uri(self) -> str:
        return f"{self.api_base_url.rstrip('/')}/api/v1/integrations/jira/callback"

    @property
    def trello_return_url(self) -> str:
        return f"{self.web_base_url.rstrip('/')}/integrations/trello/callback"

    @property
    def trello_webhook_base(self) -> str:
        return f"{self.api_base_url.rstrip('/')}/api/v1/integrations/trello/webhook"


@lru_cache
def get_settings() -> Settings:
    return Settings()
