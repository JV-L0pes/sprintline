# Cadencia API

Backend do Cadencia — monolito modular com DDD (identity, work, metrics, integrations).

## Desenvolvimento local

Requisitos: [uv](https://docs.astral.sh/uv/) (Python 3.12+).

```bash
uv sync                       # instala dependencias (cria .venv)
cp .env.example .env          # ajuste se necessario
uv run python scripts/seed_demo.py
uv run uvicorn cadencia.main:app --reload --port 8000
```

- Docs interativas: http://localhost:8000/docs
- Healthcheck: http://localhost:8000/healthz
- Banco local padrao: SQLite (`cadencia.db`); producao usa Postgres (Neon) via `CADENCIA_DATABASE_URL`.

## Qualidade

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest                     # unit + integration + e2e (SQLite em memoria)
uv run lint-imports               # fronteiras entre bounded contexts
uv run pytest --cov=cadencia --cov-report=term-missing   # cobertura
```

## Migracoes (Alembic)

```bash
uv run alembic upgrade head        # aplica schema (Postgres/Neon)
uv run alembic revision --autogenerate -m "descricao"
```

A migracao `0001` e metadata-driven; as seguintes devem ser autogeradas contra Postgres.

## Deploy (Vercel + Neon)

- Entry serverless: `api/index.py` expondo `app` (ASGI); a Vercel instala as dependencias de
  `requirements.txt` (gerado com `uv export --frozen --no-dev --no-emit-project --no-hashes`).
  Ao mudar o `pyproject.toml`, regenere: `uv lock && uv export ... -o requirements.txt`.
- Envs obrigatorias: `CADENCIA_DATABASE_URL` (endpoint `-pooler` do Neon), `CADENCIA_JWT_SECRET`,
  `CADENCIA_INTEGRATION_SECRET_KEY`, `CADENCIA_WEB_BASE_URL`, `CADENCIA_CORS_ORIGINS`, `CADENCIA_COOKIE_SECURE=true`.
- Migracoes rodam no CI (`alembic upgrade head`), nunca no cold start.
