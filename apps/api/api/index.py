"""Entrypoint da API na Vercel (runtime Python, ASGI).

A Vercel detecta a variavel `app` (ASGI) em arquivos sob `api/`. O `src/` do
projeto entra no `sys.path` porque o runtime instala apenas as dependencias de
`requirements.txt` — o pacote local nao e instalado no deploy.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cadencia.main import app

__all__ = ["app"]
