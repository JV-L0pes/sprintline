"""Objetos de valor de identidade e tenancy."""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum

from cadencia.shared.errors import ValidationError

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class Role(StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


ROLE_RANK: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.MEMBER: 1,
    Role.ADMIN: 2,
    Role.OWNER: 3,
}

DEFAULT_TIMEZONE = "America/Sao_Paulo"
DEFAULT_WORKING_DAYS: tuple[int, ...] = (0, 1, 2, 3, 4)  # segunda a sexta (0=segunda)
PASSWORD_MIN_LENGTH = 10


def role_at_least(role: Role, minimum: Role) -> bool:
    return ROLE_RANK[role] >= ROLE_RANK[minimum]


def normalize_email(raw: str) -> str:
    email = raw.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValidationError("Email invalido", code="INVALID_EMAIL")
    local, _, domain = email.partition("@")
    if not local or "." not in domain:
        raise ValidationError("Email invalido", code="INVALID_EMAIL")
    return email


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = _SLUG_RE.sub("-", normalized.lower()).strip("-")
    if not slug:
        raise ValidationError("Nome invalido para gerar identificador", code="INVALID_SLUG")
    return slug[:64]


def validate_timezone(value: str) -> str:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValidationError(f"Timezone desconhecido: {value}", code="INVALID_TIMEZONE") from exc
    return value


def validate_working_days(days: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    normalized = tuple(sorted({int(day) for day in days}))
    if not normalized or any(day < 0 or day > 6 for day in normalized):
        raise ValidationError(
            "working_days deve conter dias de 0 (segunda) a 6 (domingo)",
            code="INVALID_WORKING_DAYS",
        )
    return normalized
