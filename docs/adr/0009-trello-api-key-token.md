# ADR 0009 — Trello via API key do app + token de usuário (`/1/authorize`)

- Status: aceito
- Data: 2026-09-16
- Contexto: além do Jira, o produto deve importar boards do Trello. O Trello não oferece OAuth 2.0 3LO; o fluxo suportado é API key do aplicativo + token do usuário.

## Decisão

- O servidor guarda apenas a **API key** (`CADENCIA_TRELLO_API_KEY`); o token é obtido pelo fluxo `https://trello.com/1/authorize?response_type=token&...&return_url=...`.
- O token volta no **fragmento** da URL de retorno (o servidor não o vê): o frontend lê `#token=...` na página `/integrations/trello/callback` e o entrega via `POST /integrations/trello/connect`. Um guard de `sessionStorage` + reconexão idempotente no backend (dedupe por `member.id`) evita duplicatas mesmo com StrictMode/refresh.
- Token cifrado no mesmo `integration_tokens` (Fernet); sem refresh — expiração "never" (TTL local de 10 anos).
- **Mapeamento**: board → projeto interno (vínculo em `external_mappings`), listas → colunas por heurística de nome (done/doing/todo), cards → work items. Story points não são nativos: lê `(N)`/`[N]` no fim do nome e faz snap para Fibonacci. Labels `bug`/`story`/`epic` definem o tipo.
- **Webhooks**: registrados por board ao fim da importação (best-effort), deduplicados por `action.id`; o handler move o item conforme a lista atual do card. Reconciliação noturna continua sendo a rede de segurança.

## Consequências

- Zero fricção para o usuário: autoriza no Trello e volta conectado; sem colar chaves no app.
- Mesma infraestrutura do Jira (jobs resumíveis, mappings, vault) — conector novo custou apenas gateway + casos de uso + rotas.
- Limitação assumida: custom fields de story points (planos pagos) não são lidos nesta fase; a heurística `(N)` cobre o uso comum.
