# Sprintline

> Agile tracking with metrics your team can trust — kanban, sprints, a real burndown and live Jira/Trello integrations.

[![CI](https://github.com/JV-L0pes/sprintline/actions/workflows/ci.yml/badge.svg)](https://github.com/JV-L0pes/sprintline/actions/workflows/ci.yml)

**Português:** [README.md](README.md)

> Internal codename: `cadencia` (`@cadencia/*` packages, `cadencia` Python package, `CADENCIA_*` env vars).

**Live:** [sprintline-web.vercel.app](https://sprintline-web.vercel.app) · API + docs: [sprintline-api.vercel.app/docs](https://sprintline-api.vercel.app/docs). **Private, invite-only** access (`CADENCIA_REGISTRATION_MODE=invite_only`): an admin generates the invite link in the workspace settings; there is no open sign-up and no demo account.

---

## What this is

The project started as a static burndown chart (see `docs/PLANO-REVAMP.md` for the full diagnosis of the legacy app) and was rewritten as a tracking platform:

- **Internal Jira-style kanban**: projects, board with configurable columns (name, WIP, order and status category), hierarchical work items (Epic › Story/Task/Bug › Subtask), Fibonacci story points, drag-and-drop backlog.
- **Sprints per Scrum Guide 2020**: planning, mandatory goal, one active sprint per board, completion with explicit carryover.
- **Metrics from the event log** (`RM-01..RM-15`): burndown (working days, ideal line, visible scope changes), burnup, velocity, CFD, cycle/lead time with p50/p85/p95 percentiles.
- **Jira Cloud and Trello integrations**: Jira via OAuth 2.0 3LO (story-point field discovery, paginated/idempotent import, deduplicated webhooks); Trello via app API key + user authorization (boards → projects, lists → columns by heuristic, cards → items, story points read from `(N)` in the name, per-board webhooks).
- **Multi-workspace** with roles (owner/admin/member/viewer), quick switching from the sidebar, link invites and pt-BR/en i18n.
- **Full lifecycle**: project and item archiving (soft delete with preserved history) and real workspace deletion by the owner (full cascade, LGPD); editable workspace name/timezone and a dedicated members page.

## Architecture

```
apps/web   React 19 + Vite + Tailwind v4 + TanStack Query (FSD)
apps/api   FastAPI + async SQLAlchemy (modular monolith: identity, work, metrics, integrations)
docs/      revamp plan, ADRs, rules catalog and runbook
```

Full decisions in [`docs/adr/`](docs/adr/), the normative rules catalog in [`docs/domain/catalogo.md`](docs/domain/catalogo.md), the **case study** in [`docs/case-study.md`](docs/case-study.md) and the change history in [CHANGELOG.md](CHANGELOG.md).

## Running locally

Requirements: Node 20+, pnpm, [uv](https://docs.astral.sh/uv/) and Python 3.12 (uv downloads it if needed).

```powershell
# once per session: put uv on PATH (Windows, installed via pip)
$env:Path += ";$env:APPDATA\Python\Python314\Scripts"
# permanent: setx PATH "$env:PATH;$env:APPDATA\Python\Python314\Scripts"  (new terminal)

pnpm install
pnpm --filter @cadencia/web exec playwright install chromium   # optional (e2e)
```

```bash
# Terminal 1 — API (local SQLite, zero config)
pnpm api:seed      # creates the demo workspace with 2 sprints of history
pnpm api:dev       # http://localhost:8000 (docs at /docs)

# Terminal 2 — Web
pnpm web:dev       # http://localhost:5173 (proxy /api -> :8000)
```

The demo seed (`pnpm api:seed`) creates `demo@cadencia.dev` / `cadencia-demo-2026` **locally only** (it refuses to run in production without --force). The database lives in `apps/api/cadencia.db` (delete the file to start over). For real Jira/Trello, copy `apps/api/.env.example` to `apps/api/.env` and fill in `CADENCIA_JIRA_CLIENT_ID/SECRET` and/or `CADENCIA_TRELLO_API_KEY`.

## Quality

```bash
pnpm exec biome check .                 # formatting + base lint (JS/TS/JSON)
pnpm --filter @cadencia/web lint        # type-aware ESLint + a11y + hooks
pnpm --filter @cadencia/web exec tsc -b --noEmit
pnpm --filter @cadencia/web test:unit   # 35 Vitest + Testing Library tests
pnpm --filter @cadencia/web build

cd apps/api
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run lint-imports                     # bounded context boundaries
uv run pytest                           # 128 tests: unit, integration, API e2e
```

Real e2e (Playwright boots API+seed+web by itself):

```bash
cp apps/api/.env.example apps/api/.env   # if it does not exist yet
CADENCIA_E2E=1 pnpm --filter @cadencia/web test:e2e   # set UV_BIN if uv is not on PATH
```

CI (`.github/workflows/ci.yml`) runs all of the above, applies Alembic migrations on a real Postgres, runs the seed as a smoke test and runs gitleaks/pip-audit.

## Deploy (Vercel + Neon)

Projects: **`sprintline-api`** (root `apps/api`) and **`sprintline-web`** (root `apps/web`). The web app proxies `/api/*` same-origin to the API project (`apps/web/vercel.json`), so session cookies stay first-party and `VITE_API_URL` stays empty in production.

```bash
npx vercel login                     # once
cd apps/api && npx vercel link       # create the sprintline-api project
cd ../web && npx vercel link         # create the sprintline-web project
```

1. **Neon**: create the database and use the `-pooler` endpoint (`postgresql+asyncpg://...`).
2. **API envs** (Vercel → sprintline-api): `CADENCIA_DATABASE_URL`, `CADENCIA_JWT_SECRET`,
   `CADENCIA_INTEGRATION_SECRET_KEY`, `CADENCIA_WEB_BASE_URL=https://sprintline-web.vercel.app`,
   `CADENCIA_CORS_ORIGINS=https://sprintline-web.vercel.app`, `CADENCIA_COOKIE_SECURE=true`,
   `CADENCIA_REGISTRATION_MODE=invite_only` (ADR 0010).
   Entry: `api/index.py` (ASGI auto-detected; deps via `requirements.txt`).
   After deploying, create the first owner: `uv run python scripts/create_admin.py --email ... --name ...`.
3. **Web envs** (sprintline-web): none required (same-origin proxy); optional `VITE_API_URL`.
4. **Deploy**: connect both projects to the repository (automatic deploys on every push) — or
   `npx vercel --prod` from the repo root after `npx vercel link --project sprintline-api|sprintline-web`
   (with Root Directory configured, the CLI must run from the root). If a push does not trigger a deploy,
   check `npx vercel ls <project>` and trigger it manually.
5. **Migrations**: `CADENCIA_DATABASE_URL=<neon> uv run alembic upgrade head` (local/CI; never on cold start).
6. **Jira**: create a 3LO app at https://developer.atlassian.com/console/myapps/ with redirect
   `https://sprintline-api.vercel.app/api/v1/integrations/jira/callback` and set `CADENCIA_JIRA_CLIENT_ID/SECRET`.
7. **Trello**: create an API key at https://trello.com/power-ups/admin and set `CADENCIA_TRELLO_API_KEY`;
   the user authorizes from inside the app (the token returns to `/integrations/trello/callback`).

Operational details in [`docs/runbook/operacao.md`](docs/runbook/operacao.md).

## Folder structure

```
apps/api/src/cadencia/
  shared/            kernel (entities, events, errors, ids, clock)
  platform/          cross-cutting infra (db, security, event log, handlers)
  identity/          auth, workspaces, members, invites
  work/              projects, board, work items, sprints, backlog
  metrics/           pure calculators + event log readers
  integrations/      Jira OAuth/import/webhooks
apps/web/src/
  app/ pages/ widgets/ features/ entities/ shared/    (FSD)
packages/tsconfig   shared tsconfig presets
```

## Roadmap

Phases 0–7 in [`docs/PLANO-REVAMP.md`](docs/PLANO-REVAMP.md#10-roadmap-por-fases). **Phases 0–6 delivered** and running in private production, with the **Trello** connector anticipated from Phase 7 (Jira/Trello webhooks already live, with dedupe). Still open from the original vision: metric snapshots via cron + nightly reconciliation, notifications, CSV/PDF export, public API with tokens, Monte Carlo forecasting and extra hardening (Sentry, k6).

## License

MIT — see [LICENSE](LICENSE). Author: João Victor ([JV-L0pes](https://github.com/JV-L0pes)).
