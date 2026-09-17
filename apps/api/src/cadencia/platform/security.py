"""Hash de senha (Argon2id), JWT de acesso e tokens de refresh opacos."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from cadencia.platform.config import Settings
from cadencia.shared.errors import UnauthorizedError

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(
    *,
    user_id: uuid.UUID,
    settings: Settings,
    now: datetime,
    token_id: uuid.UUID | None = None,
) -> tuple[str, datetime]:
    expires_at = now + timedelta(minutes=settings.access_token_ttl_minutes)
    claims = {
        "sub": str(user_id),
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "typ": "access",
        "jti": str(token_id or uuid.uuid4()),
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "exp", "iss", "typ"]},
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Token de acesso inválido ou expirado") from exc
    if claims.get("typ") != "access":
        raise UnauthorizedError("Tipo de token inválido")
    try:
        return uuid.UUID(str(claims["sub"]))
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Token de acesso inválido") from exc


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def hash_opaque_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def encode_state_token(
    claims: dict[str, str], *, settings: Settings, now: datetime, ttl_minutes: int = 10
) -> str:
    payload = {
        **claims,
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_state_token(token: str, *, settings: Settings) -> dict[str, str]:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iss"]},
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("State OAuth inválido ou expirado") from exc
    return {str(key): str(value) for key, value in claims.items()}


def webhook_token(connection_id: str, settings: Settings) -> str:
    """Segredo de URL para webhooks públicos (sem assinatura nativa no 3LO)."""
    digest = hashlib.sha256(f"{connection_id}:{settings.jwt_secret}".encode()).hexdigest()
    return digest[:32]
