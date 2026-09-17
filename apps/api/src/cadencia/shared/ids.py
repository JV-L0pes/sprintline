"""UUIDv7 (RFC 9562) — ids ordenaveis por tempo, gerados sem dependencia externa."""

from __future__ import annotations

import os
import time
import uuid

_RAND_A_BITS = 12
_RAND_B_BITS = 62


def uuid7() -> uuid.UUID:
    """Gera um UUIDv7 monotonicamente crescente por milissegundo."""
    ts_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand_a = int.from_bytes(os.urandom(2), "big") & ((1 << _RAND_A_BITS) - 1)
    rand_b = int.from_bytes(os.urandom(8), "big") & ((1 << _RAND_B_BITS) - 1)
    value = (ts_ms << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return uuid.UUID(int=value)
