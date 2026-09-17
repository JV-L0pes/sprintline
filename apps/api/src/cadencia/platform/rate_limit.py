"""Rate limit persistido (funciona em serverless, sem Redis).

Janela fixa por chave: `chave -> (inicio_da_janela, contador)`. Volume baixo
(single-digit usuários), então o read-modify-write dentro da transacao da
request e suficiente; colisoes no pior caso afrouxam levemente o limite.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from cadencia.platform.orm import RateLimitHitRow
from cadencia.shared.clock import Clock
from cadencia.shared.errors import RateLimitError


class RateLimiter:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    async def enforce(
        self, key: str, *, limit: int, window_minutes: int, label: str | None = None
    ) -> None:
        now = self._clock.now()
        window = timedelta(minutes=window_minutes)
        row = await self._session.get(RateLimitHitRow, key)

        if row is None or now - _ensure_utc(row.window_start) >= window:
            if row is None:
                self._session.add(RateLimitHitRow(key=key, window_start=now, count=1))
            else:
                row.window_start = now
                row.count = 1
            await self._session.flush()
            # O contador precisa sobreviver ao rollback de uma request que falha
            # (ex.: 401 no login), então commitamos imediatamente.
            await self._session.commit()
            return

        if row.count >= limit:
            retry_after = max(
                1, int((_ensure_utc(row.window_start) + window - now).total_seconds())
            )
            alvo = f" de {label}" if label else ""
            raise RateLimitError(
                f"Muitas tentativas{alvo}. Tente novamente em {retry_after}s.",
                retry_after_seconds=retry_after,
            )

        row.count += 1
        await self._session.flush()
        await self._session.commit()

    async def clear(self, key: str) -> None:
        await self._session.execute(sa.delete(RateLimitHitRow).where(RateLimitHitRow.key == key))
        await self._session.flush()
        await self._session.commit()


def _ensure_utc(moment: datetime) -> datetime:
    from cadencia.platform.db import ensure_utc

    return ensure_utc(moment) or moment


def client_ip(request_headers_forwarded_for: str | None, fallback: str | None) -> str:
    """Vercel repassa o IP real em x-forwarded-for (primeiro da lista)."""
    if request_headers_forwarded_for:
        return request_headers_forwarded_for.split(",")[0].strip()
    return fallback or "unknown"
