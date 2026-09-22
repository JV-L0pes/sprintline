# Cadencia API

Backend do Cadencia — monolito modular com DDD (identity, work, metrics, integrations).

## Desenvolvimento local

Requisitos: [uv](https://docs.astral.sh/uv/) (Python 3.12+).

```bash
uv sync                       # instala dependências (cria .venv)
cp .env.example .env          # ajuste se necessario
uv run python scripts/seed_demo.py   # dados de demonstração (só local; recusa produção sem --force)
uv run uvicorn cadencia.main:app --reload --port 8000
```

- Docs interativas: http://localhost:8000/docs
- Healthcheck: http://localhost:8000/healthz
- Banco local padrão: SQLite (`cadencia.db`); produção usa Postgres (Neon) via `CADENCIA_DATABASE_URL`.

## Instância privada (invite-only)

- `CADENCIA_REGISTRATION_MODE`: `invite_only` (padrão), `open` ou `closed`.
- Primeiro owner (obrigatório em instância fechada):
  `uv run python scripts/create_admin.py --email você@exemplo.com --name "Seu Nome"`.
- Convites: admin gera o link (`POST .../invites`) e a pessoa cadastra-se com `invite_token`.
- Rate limit: login 10/15min, registro 5/h, refresh 120/h (configurável por env; 429 + `Retry-After`).
- Limpeza de demo em produção: `uv run python scripts/purge_demo.py --yes`.

## Qualidade

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest                     # unit + integration + e2e (SQLite em memória)
uv run lint-imports               # fronteiras entre bounded contexts
uv run pytest --cov=cadencia --cov-report=term-missing   # cobertura
```

## Migrações (Alembic)

```bash
uv run alembic upgrade head        # aplica schema (Postgres/Neon)
uv run alembic revision --autogenerate -m "descrição"
```

A migração `0001` é metadata-driven; as seguintes devem ser autogeradas contra Postgres.

## Deploy (Vercel + Neon)

- Entry serverless: `api/index.py` expondo `app` (ASGI); a Vercel instala as dependências de
  `requirements.txt` (gerado com `uv export --frozen --no-dev --no-emit-project --no-hashes`).
  Ao mudar o `pyproject.toml`, regenere: `uv lock && uv export ... -o requirements.txt`.
- Envs obrigatórias: `CADENCIA_DATABASE_URL` (endpoint `-pooler` do Neon), `CADENCIA_JWT_SECRET`,
  `CADENCIA_INTEGRATION_SECRET_KEY`, `CADENCIA_WEB_BASE_URL`, `CADENCIA_CORS_ORIGINS`, `CADENCIA_COOKIE_SECURE=true`,
  `CADENCIA_REGISTRATION_MODE=invite_only` (ver ADR 0010).
- Migrações rodam no CI (`alembic upgrade head`), nunca no cold start.
- Após o primeiro deploy, rode o bootstrap do owner: `uv run python scripts/create_admin.py ...`.
