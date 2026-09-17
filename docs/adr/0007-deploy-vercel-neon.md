# ADR 0007 — Vercel + Neon (free), com portabilidade por container

- Status: aceito
- Data: 2026-09-16
- Contexto: custo zero no início, deploy simples, banco Postgres gerenciado com branches para preview.

## Decisão

- `apps/web` estático na Vercel; `apps/api` serverless (runtime Python ASGI — a Vercel detecta o `app` exportado em `api/index.py`; dependências via `requirements.txt`, com `src/` injetado no `sys.path`).
- Postgres no Neon via endpoint `-pooler`; SQLAlchemy com `NullPool` e prepared statements desabilitados (pgbouncer).
- Migrações Alembic rodam no CI, nunca no cold start.
- Limitações assumidas: sem WebSocket (UI usa polling), timeout curto (import em chunks resumíveis), cron diário no plano Hobby (snapshot noturno self-healing). `infra/docker/Dockerfile.api` mantém a saída para Fly.io/Render/VPS sem mudança de código.

## Consequências

- Operação barata e reproduzível; qualquer limitação de plataforma é contornada no design, não no código de negócio.
