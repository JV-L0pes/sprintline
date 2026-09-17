# ADR 0008 — Integração Jira Cloud via OAuth 2.0 (3LO) + webhooks dinâmicos

- Status: aceito
- Data: 2026-09-16
- Contexto: o objetivo é importar projetos/issues reais do Jira e manter sincronização sem intervenção manual.

## Decisão

OAuth 2.0 3LO com escopos `read:jira-work`, `write:jira-work`, `read:jira-user`, `offline_access` e `manage:jira-webhook`; tokens criptografados em repouso (Fernet). Story points e sprint são **custom fields cuja ID varia por instância**: descoberta automática (`/rest/api/3/field`) + confirmação do usuário. Import paginado e resumível (`sync_jobs.cursor`), idempotente por `(connection, external_id)`; escrita local sempre via casos de uso do contexto `work` (nunca SQL direto). Webhooks com deduplicação `(connection, external_event_id)` e segredo no path.

## Consequências

- Sincronização incremental viável; reconcilição noturna corrige drift (Fase 5 do roadmap).
- Import de sprints/webhooks registrados ficam como evolução incremental da mesma estrutura.
