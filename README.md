# Sprintline

> Tracking ágil com métricas que o time confia — kanban, sprints, burndown de verdade e integrações reais com Jira e Trello.

[![CI](https://github.com/JV-L0pes/sprintline/actions/workflows/ci.yml/badge.svg)](https://github.com/JV-L0pes/sprintline/actions/workflows/ci.yml)

**English:** Sprintline is an agile tracking platform: an internal Jira-style kanban/backlog feeds an append-only event log from which burndown, velocity, CFD and flow metrics are computed. The backend is a modular monolith (FastAPI + DDD bounded contexts); the frontend is a React/Vite SPA built with the "Ink" design system (Tailwind v4). See `docs/` for architecture decisions.

> Codename interno: `cadencia` (pacotes `@cadencia/*`, pacote Python `cadencia`, envs `CADENCIA_*`).

**Demo:** [sprintline-web.vercel.app](https://sprintline-web.vercel.app) · API + docs: [sprintline-api.vercel.app/docs](https://sprintline-api.vercel.app/docs) · login `demo@cadencia.dev` / `cadencia-demo-2026` (workspace de demonstração).

---

## O que é isto

O projeto nasceu como um burndown chart estático (veja `docs/PLANO-REVAMP.md` para o diagnóstico completo do legado) e foi reescrito como uma plataforma de tracking:

- **Kanban interno** estilo Jira: projetos, board por categorias (To Do / In Progress / Done), work items hierárquicos (Epic › Story/Task/Bug › Subtask), story points Fibonacci, WIP limits, backlog com drag-and-drop.
- **Sprints com Scrum Guide 2020**: planejamento, objetivo obrigatório, uma sprint ativa por board, conclusão com carryover explícito.
- **Métricas do event log** (`RM-01..RM-15`): burndown (dias úteis, linha ideal, mudanças de escopo visíveis), burnup, velocity, CFD, cycle/lead time com percentis p50/p85/p95.
- **Integrações Jira Cloud e Trello**: Jira via OAuth 2.0 3LO (descoberta de campos de story points, import paginado/idempotente, webhooks deduplicados); Trello via API key do app + autorização do usuário (boards → projetos, listas → colunas por heurística, cards → itens, story points lidos de `(N)` no nome, webhooks por board).
- **Multi-workspace** com papéis (owner/admin/member/viewer), convites por link e i18n pt-BR/en.

## Arquitetura

```
apps/web   React 19 + Vite + Tailwind v4 + TanStack Query (FSD)
apps/api   FastAPI + SQLAlchemy async (monolito modular: identity, work, metrics, integrations)
docs/      plano de revamp, ADRs, catálogo de regras e runbook
```

Decisões completas em [`docs/adr/`](docs/adr/) e o catálogo normativo de regras em [`docs/domain/catalogo.md`](docs/domain/catalogo.md).

## Rodando localmente

Pré-requisitos: Node 20+, pnpm, [uv](https://docs.astral.sh/uv/) e Python 3.12 (o uv baixa se precisar).

```powershell
# uma vez por sessão: coloque o uv no PATH (Windows, instalado via pip)
$env:Path += ";$env:APPDATA\Python\Python314\Scripts"
# permanente: setx PATH "$env:PATH;$env:APPDATA\Python\Python314\Scripts"  (novo terminal)

pnpm install
pnpm --filter @cadencia/web exec playwright install chromium   # opcional (e2e)
```

```bash
# Terminal 1 — API (SQLite local, sem configurar nada)
pnpm api:seed      # cria o workspace demo com 2 sprints de histórico
pnpm api:dev       # http://localhost:8000 (docs em /docs)

# Terminal 2 — Web
pnpm web:dev       # http://localhost:5173 (proxy /api -> :8000)
```

Credenciais da demo: `demo@cadencia.dev` / `cadencia-demo-2026`. O banco fica em
`apps/api/cadencia.db` (apague o arquivo para recomeçar). Para Jira/Trello reais, copie
`apps/api/.env.example` para `apps/api/.env` e preencha `CADENCIA_JIRA_CLIENT_ID/SECRET`
e/ou `CADENCIA_TRELLO_API_KEY`.

## Qualidade

```bash
pnpm exec biome check .                 # formatação + lint base (JS/TS/JSON)
pnpm --filter @cadencia/web lint        # ESLint type-aware + a11y + hooks
pnpm --filter @cadencia/web exec tsc -b --noEmit
pnpm --filter @cadencia/web test:unit   # 29 testes Vitest + Testing Library + MSW
pnpm --filter @cadencia/web build

cd apps/api
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run lint-imports                     # fronteiras entre bounded contexts
uv run pytest                           # 108 testes: unit, integration, e2e de API
```

E2E real (Playwright sobe API+seed+web sozinho):

```bash
cp apps/api/.env.example apps/api/.env   # se ainda nao existir
CADENCIA_E2E=1 pnpm --filter @cadencia/web test:e2e   # defina UV_BIN se o uv nao estiver no PATH
```

O CI (`.github/workflows/ci.yml`) roda tudo isso, aplica as migrações Alembic em um Postgres real, executa o seed como smoke test e roda gitleaks/pip-audit.

## Deploy (Vercel + Neon)

Projetos: **`sprintline-api`** (root `apps/api`) e **`sprintline-web`** (root `apps/web`).
O web faz proxy same-origin de `/api/*` para o projeto da API (`apps/web/vercel.json`), então
os cookies de sessão continuam first-party e `VITE_API_URL` fica vazio em produção.

```bash
npx vercel login                     # uma vez
cd apps/api && npx vercel link       # crie o projeto sprintline-api
cd ../web && npx vercel link         # crie o projeto sprintline-web
```

1. **Neon**: crie o banco e use o endpoint `-pooler` (`postgresql+asyncpg://...`).
2. **Envs da API** (Vercel → sprintline-api): `CADENCIA_DATABASE_URL`, `CADENCIA_JWT_SECRET`,
   `CADENCIA_INTEGRATION_SECRET_KEY`, `CADENCIA_WEB_BASE_URL=https://sprintline-web.vercel.app`,
   `CADENCIA_CORS_ORIGINS=https://sprintline-web.vercel.app`, `CADENCIA_COOKIE_SECURE=true`.
   Entry: `api/index.py` (ASGI detectado automaticamente; deps via `requirements.txt`).
3. **Envs do web** (sprintline-web): nenhuma obrigatória (proxy same-origin); opcional `VITE_API_URL`.
4. **Deploy**: `npx vercel --prod` em cada pasta — ou conecte os dois projetos ao repo e deixe o Git cuidar.
5. **Migrações**: `CADENCIA_DATABASE_URL=<neon> uv run alembic upgrade head` (local/CI; nunca no cold start).
6. **Jira**: crie um app 3LO em https://developer.atlassian.com/console/myapps/ com redirect
   `https://sprintline-api.vercel.app/api/v1/integrations/jira/callback` e configure `CADENCIA_JIRA_CLIENT_ID/SECRET`.
7. **Trello**: crie uma API key em https://trello.com/power-ups/admin e configure `CADENCIA_TRELLO_API_KEY`;
   o usuário autoriza pelo próprio app (o token volta para `/integrations/trello/callback`).

Detalhes operacionais em [`docs/runbook/operacao.md`](docs/runbook/operacao.md).

## Estrutura de pastas

```
apps/api/src/cadencia/
  shared/            kernel (entidades, eventos, erros, ids, clock)
  platform/          infra transversal (db, segurança, event log, handlers)
  identity/          auth, workspaces, membros, convites
  work/              projetos, board, work items, sprints, backlog
  metrics/           calculadoras puras + leitura do event log
  integrations/      Jira OAuth/import/webhooks
apps/web/src/
  app/ pages/ widgets/ features/ entities/ shared/    (FSD)
```

## Roadmap

Fases 0–7 em [`docs/PLANO-REVAMP.md`](docs/PLANO-REVAMP.md#10-roadmap-por-fases). Concluído nesta entrega: fundação, identidade/tenancy, work management, kanban/backlog, métricas e a base da integração Jira. Próximo: registração de webhooks + reconciliação noturna, snapshots via cron, hardening (Sentry, k6) e forecasting Monte Carlo.

## Licença

MIT — veja [LICENSE](LICENSE). Autor: João Victor ([JV-L0pes](https://github.com/JV-L0pes)).
