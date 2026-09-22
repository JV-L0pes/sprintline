# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e versionamento semântico.

## [0.1.0] — 2026-09-21

Primeira entrega completa: a reescrita do burndown estático para uma plataforma de tracking ágil, rodando em produção privada (Vercel + Neon).

### Adicionado

- **Kanban interno** estilo Jira: projetos com chave derivada do nome, board com colunas configuráveis (nome, WIP, ordem e categoria de status editável com guarda de cobertura), work items hierárquicos (Epic › Story/Task/Bug › Subtask), story points Fibonacci e backlog com drag-and-drop.
- **Sprints (Scrum Guide 2020)**: planejamento, objetivo obrigatório, uma sprint ativa por board e conclusão com carryover explícito.
- **Métricas do event log** (`RM-01..RM-15`): burndown com dias úteis, linha ideal e mudanças de escopo visíveis; burnup; velocity; CFD; cycle/lead time com percentis p50/p85/p95.
- **Integração Jira Cloud** (OAuth 2.0 3LO): descoberta automática do campo de story points, import paginado e idempotente, webhooks deduplicados e jobs com progresso/erro consultáveis.
- **Integração Trello** (API key + autorização do usuário): boards → projetos, listas → colunas por heurística, cards → itens, story points lidos de `(N)` no nome e webhooks por board.
- **Multi-workspace**: papéis (owner/admin/member/viewer), convites por link com expiração, troca rápida de workspace na barra lateral e páginas próprias de Membros e Configurações.
- **Ciclo de vida**: arquivamento de projetos e itens (soft delete com histórico preservado) e exclusão real de workspace pelo owner, com cascata completa (LGPD).
- **Configurações do workspace**: renomear e trocar o fuso horário (admin+), com eventos auditados.
- **Instância privada**: registro invite-only por padrão, bootstrap do primeiro owner por script e purge de dados de demonstração.
- **Rate limit** de login/registro/refresh com `429` + `Retry-After`, persistido fora do rollback.
- **Design system Ink** aplicado ao produto: dourado racionado a sinal (status, marca, marcador de seção e foco), select listbox próprio com teclado, tema claro/escuro e i18n pt-BR/en.

### Alterado

- Repositório renomeado de `burndown-chart` para `sprintline` (codename interno `cadencia` permanece nos pacotes e envs).
- Registro público substituído por convite (ADR 0010); conta de demonstração removida da produção.

### Corrigido

- Acentuação pt-BR em toda a UI, mensagens da API e documentação.
- Alinhamento do select e do input de WIP (line-height e largura em grids de formulário).
- Painel do select fechava ao rolar a própria lista; agora só fecha com scroll externo.
- Import do Trello falhava com códigos que não eram label válido (normalização por nome).

### Segurança

- Senhas com Argon2id; sessões JWT com refresh rotativo em cookie httpOnly; tokens de integração cifrados com Fernet.
- CI com `gitleaks`, `pip-audit` e `pnpm audit`; segredos exclusivamente por variáveis de ambiente.
