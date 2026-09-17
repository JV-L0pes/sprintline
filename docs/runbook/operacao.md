# Runbook de operação — Cadencia

## Ambientes

| Ambiente | Web | API | Banco |
|---|---|---|---|
| Local | `pnpm web:dev` (`:5173`, proxy `/api`) | `uv run uvicorn cadencia.main:app --reload` (`:8000`) | SQLite `apps/api/cadencia.db` |
| Preview (PR) | Vercel Preview | Vercel Preview | Branch Neon efêmera (ou `dev`) |
| Produção | Vercel | Vercel (Mangum) | Neon `main` (endpoint `-pooler`) |

## Variáveis de ambiente da API

| Variável | Obrigatória | Notas |
|---|---|---|
| `CADENCIA_DATABASE_URL` | prod | `postgresql+asyncpg://...-pooler...` |
| `CADENCIA_JWT_SECRET` | prod | ≥32 bytes aleatórios |
| `CADENCIA_INTEGRATION_SECRET_KEY` | prod | chave Fernet (base64 url-safe 32B) p/ tokens do Jira |
| `CADENCIA_WEB_BASE_URL` | prod | URL do app (redirects OAuth) |
| `CADENCIA_CORS_ORIGINS` | prod | domínios da web, CSV |
| `CADENCIA_COOKIE_SECURE` | prod | `true` |
| `CADENCIA_JIRA_CLIENT_ID/SECRET` | Jira | app 3LO |
| `CADENCIA_TRELLO_API_KEY` | Trello | API key do app (trello.com/power-ups/admin); token vem do fluxo `/1/authorize` |

Gerar segredos: `python -c "import secrets; print(secrets.token_urlsafe(48))"` e
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

## Instância privada (invite-only)

- `CADENCIA_REGISTRATION_MODE`: `invite_only` (padrão) bloqueia cadastro aberto; `open` libera; `closed` desliga o endpoint.
- **Bootstrap do primeiro owner** (obrigatório em instância fechada):
  `uv run python scripts/create_admin.py --email voce@exemplo.com --name "Seu Nome"` (gera senha temporária; troque no primeiro acesso).
- Convites: um admin gera o link em Configurações → Membros → Convidar; a pessoa abre o link, cria a conta e entra.
- Rate limit do auth: login 10 tentativas/15min, registro 5/h, refresh 120/h (configurável por env); resposta 429 com `Retry-After`.
- **Remover dados de demonstração** de um banco: `uv run python scripts/purge_demo.py --yes` (o seed local recusa rodar em produção sem `--force`).

## Migrações

```bash
cd apps/api
uv run alembic upgrade head                       # aplica
uv run alembic revision --autogenerate -m "..."   # nova migração (revisar sempre)
uv run alembic downgrade -1                       # rollback de uma revisão
```

Nunca rode migrações no cold start da função serverless. Em produção: job do CI ou execução manual controlada.

## Cron noturno (Fase 5+)

Job diário na Vercel (plano Hobby permite 2 crons/dia) deve:
1. Materializar snapshots de métricas de sprints ativas (`(sprint_id, date)` idempotente, reprocessa dias ausentes).
2. Reconciliar integrações Jira (comparar `updated` no período e corrigir drift).
3. Renovar webhooks dinâmicos antes da expiração.

## Backups

- Neon mantém PITR/janela do plano; verifique a janela vigente.
- Export semanal: `pg_dump "$CADENCIA_DATABASE_URL" -Fc -f cadencia-$(date +%F).dump` para storage externo.

## Incidentes comuns

| Sintoma | Diagnóstico | Ação |
|---|---|---|
| 500 em toda a API | cold start + conectividade Neon | checar logs JSON na Vercel; testar `SELECT 1` com `psql` |
| Usuário "deslogado" aleatoriamente | cookie expirado/rotação | esperado após 30 dias ou reuso detectado; re-login |
| Burndown vazio | sprint sem items/eventos | verificar `domain_events` da sprint; rodar seed de novo em dev |
| Import Jira parado | job `FAILED`/`PENDING` | `GET .../jobs` mostra `last_error`; re-rodar lote (`/run`) |
| WIP não bloqueia | projeto em modo `SOFT` | é intencional (alerta); `HARD` bloqueia |

## Higiene

- Rotação de segredos: JWT exige re-login em massa; planeje janela.
- Purge de workspace (LGPD): cascata completa via `ON DELETE CASCADE` (sessions, events, tokens).
- Logs: JSON em produção (`platform/logging.py`); nunca logar tokens/senhas (wrappers não expõem PII).
