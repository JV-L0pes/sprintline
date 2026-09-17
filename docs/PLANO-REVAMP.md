# Plano de Revamp — Burndown Chart → Plataforma de Tracking Ágil

> Documento vivo. Versão 1.0 — 2026-09-16.
> Autor: João Victor Lopes (JV-L0pes). Status: **aguardando aprovação para iniciar Fase 0**.

---

## 1. Sumário executivo

O projeto atual é um gerador de burndown chart estático, com integração Trello **fictícia** e dados mockados. O objetivo deste revamp é transformá-lo em uma plataforma de tracking ágil de verdade:

- **Kanban/backlog interno** (estilo Jira) como fonte primária de dados.
- **Métricas calculadas do zero a partir de um event log imutável**: burndown, burnup, velocity, CFD, cycle/lead time.
- **Integração real com Jira Cloud** (OAuth 2.0 3LO + webhooks + reconciliação).
- **Arquitetura de referência**: monorepo, monolito modular com DDD e bounded contexts (backend), FSD (frontend), design system baseado no portfólio "Ink".
- **Padrões internacionais** adotados: Scrum Guide 2020, Kanban Guide, convenções Jira, ISO 8601, RFC 9457 (Problem Details), Conventional Commits, SemVer, ADRs.
- **Qualidade**: linters (Ruff + Biome + ESLint), tipagem estrita, pirâmide de testes completa, CI com gates, segurança OWASP.

Decisões confirmadas pelo autor:

| Decisão | Escolha |
|---|---|
| Deploy | Vercel (web + API) + Neon Postgres (free tier) |
| Integração Jira | Jira Cloud + OAuth 2.0 (3LO) |
| Multi-tenancy | Multi-workspace desde o início |
| Idioma | pt-BR (padrão) + en |
| Auth | Email + senha, JWT access/refresh, Argon2id |
| Banco | PostgreSQL (Neon, serverless) |

Estimativa total: **~55 a 80 dev-days** em 8 fases, viável em 3–4 meses part-time com dogfooding a partir da Fase 3.

---

## 2. Diagnóstico do projeto atual

### 2.1 O que existe

```
burndown-chart/            (último commit: 2025-09-25)
├── index.html             home estática (só carrega theme.js — nenhum JS de app)
├── pages/graph.html       página do gráfico (Chart.js via CDN)
├── css/index.css (498 l)  estilo da home
├── css/graph.css (689 l)  estilo do gráfico
├── js/theme.js            toggle de tema funcional (light/dark)
├── js/graph.js (729 l)    gráfico + "integração Trello" + métricas
├── js/config.js (75 l)    configuração de sprints (código morto)
├── js/index.js (34 l)     orquestrador (código morto)
├── data/*.json            2 arquivos mock (sprint 1 de 2 grupos)
├── .github/workflows/     deploy GitHub Pages
└── package.json           scripts falsos (build = echo, test = exit 1)
```

### 2.2 Defeitos e problemas concretos (verificados no código)

| # | Severidade | Problema | Evidência |
|---|---|---|---|
| 1 | Crítico | A "integração com Trello" é 100% fictícia: valida credenciais contra `window.CREDENTIALS`, mas `js/credentials.js` **não existe no repositório** → qualquer credencial é inválida e o gráfico nunca carrega pelo fluxo principal. | `pages/graph.html:110`, `js/graph.js:46,102-106,290-295` |
| 2 | Crítico | Sprint 2 e 3 são oferecidas no seletor, mas só existem dados da sprint 1 → erro garantido. | `pages/graph.html:54-58`, `js/graph.js:86-91`, `data/` só tem `*-sprint1.json` |
| 3 | Alto | A linha ideal é matematicamente inconsistente: divide por `labels.length - 1` (7 labels) enquanto o JSON declara `totalDias: 30` — três fontes de verdade para "duração". | `js/graph.js:191-197`, `data/errorsquad-sprint1.json:7` |
| 4 | Alto | "Restante" é derivado como `total − completado`, ignorando mudanças de escopo e qualquer evento real; não há event log. Impossível calcular velocity/CFD/cycle time. | `js/graph.js:384-389` |
| 5 | Alto | Percentuais geram `NaN` quando totais são 0 (`completed / 0`). | `js/graph.js:208-209` |
| 6 | Médio | Título da sprint nunca atualiza: compara `'sprint-3'` (string) com o retorno numérico de `getSprintNumberFromUrl()`. | `js/graph.js:369-375` |
| 7 | Médio | `innerHTML` com dados que virão de API → vetor de XSS. | `js/graph.js:256-272` |
| 8 | Médio | Tokens em `localStorage` em texto puro; credenciais demo pensadas para ir ao client. | `js/graph.js:45-46,117-126,298-300` |
| 9 | Médio | Código morto: `js/index.js` importa `initializeGraph`/`updateGraph` de `graph.js`, que não exporta nada; nenhum HTML carrega `index.js`; `config.js` só é importado por `index.js`. | `js/index.js:2`, `js/config.js`, `index.html:12-13` |
| 10 | Médio | `loadConfig()` quebra com `localStorage` parcial/incompatível (acessa `parsed.sprints['sprint-1']` sem validar). | `js/config.js:62-71` |
| 11 | Médio | CDNs sem `integrity`/`crossorigin` e Chart.js sem versão fixa; sem CSP. | `index.html:9-13`, `pages/graph.html:9-10,109` |
| 12 | Baixo | Modal sem `aria-modal`, sem focus trap, sem fechar com Esc; gráfico (canvas) sem alternativa textual. | `pages/graph.html:28-47` |
| 13 | Baixo | README descreve estrutura que não existe (`css/style.css`, `js/metrics.js`, `pages/metrics.html`, `reference/`). | `README.md:52-65` |
| 14 | Baixo | Lógica duplicada (checagem de credenciais em 2 lugares, leitura de cores do tema repetida) e função morta `updateMetricsWithAnimation`. | `js/graph.js:102-106,290-295,606-650` |
| 15 | Processo | Zero testes, zero lint, zero type-check, CI só faz publicar GH Pages; `package.json` finge scripts de build/test. | `package.json:6-11`, `.github/workflows/deploy.yml` |

### 2.3 O que merece ser preservado

- **Intenção de produto**: burndown como métrica central de acompanhamento de sprint.
- **Ambição visual e dark/light theme** (`js/theme.js` é o único módulo limpo e funcional — a lógica dele é portada para o novo design system).
- **Datasets demo** (`data/*.json`) como inspiração para o seed de demonstração.
- **Licença MIT, autoria e backlinks** — o repo antigo pode virar legado arquivado apontando para o novo.
- O valor de portfólio: o revamp documenta decisões (ADRs) e vira peça de case study, no padrão do portfólio do autor.

### 2.4 Veredito

> O código atual **não é reaproveitável como base técnica** (arquitetura, testes, segurança e integração inexistentes). Ele será substituído integralmente; o que se aproveita é o domínio, o intento visual e os dados de demonstração. Este plano assume **reescrita**, não refatoração incremental.

---

## 3. Visão do produto

### 3.1 Proposta

> "Tracker ágil interno que gera métricas confiáveis — e conversa com o Jira quando a equipe já vive lá."

### 3.2 Funcionalidades (escopo-alvo)

**Núcleo local (fonte primária):**
1. Autenticação e gestão de organização/workspace/equipe (multi-tenant).
2. Projetos com quadro Kanban configurável (colunas ↔ categorias de status Jira: `To Do` / `In Progress` / `Done`).
3. Work items hierárquicos: Epic → Story/Task/Bug → Subtask; prioridade, labels, assignee, story points (Fibonacci), due date.
4. Backlog com drag-and-drop, sprint planning (criar sprint, puxar itens, capacidade), ciclo de vida da sprint (planning → active → completed).
5. WIP limits por coluna (limite mole com alerta, configurável).
6. Métricas geradas do event log: burndown, burnup, velocity, CFD, cycle/lead time, sprint report.
7. Modo demo público com dataset seed (portfólio + e2e).

**Integração:**
8. Jira Cloud real: conectar (OAuth 2.0 3LO), importar projeto/board/sprints/issues, sync por webhook + reconciliação noturna, mapeamento de campos (story points e sprint são custom fields com IDs variáveis por instância).

**Extensões (pós-MVP):**
9. Forecasting Monte Carlo, notificações, relatórios exportáveis, API pública com tokens, conector Trello opcional (arquitetura já preparada para múltiplos providers).

### 3.3 Fora de escopo (por agora)

- Tempo real via WebSocket (limitação do alvo serverless — usar polling com TanStack Query `refetchInterval`; ver Riscos).
- Edição de workflow estilo Jira (workflow builder). Colunas = mapeamento simples de categorias.
- App mobile nativo, SSO corporativo, billing.

### 3.4 Nome do produto

Placeholder do monorepo: `agile-tracker`. Sugestões de nome definitivo (decidir na Fase 0): **Cadência**, **Sprintline**, **Traço** (mantém o "Ink" do portfólio). Recomendação: manter repo novo em `JV-L0pes/<nome>` com README apontando o legado.

---

## 4. Padrões e convenções adotados (normativo)

Esta seção é a **especificação normativa** do produto. Toda regra tem ID (`RN-*` para negócio, `RM-*` para métricas) e deve ter teste automatizado correspondente.

### 4.1 Referências internacionais

| Área | Padrão | Uso no projeto |
|---|---|---|
| Processo | **Scrum Guide 2020** (Schwaber/Sutherland) | vocabulário canônico: Product Backlog, Sprint Backlog, Sprint Goal, Increment, Definition of Done |
| Fluxo | **Kanban Guide** (Vacanti/Coleman, 2020) | WIP limits, classes de serviço, Little's Law para capacidade |
| Métricas | **EBM** (Evidence-Based Management) + convenções Jira/Atlassian | velocity, cycle/lead time, throughput, percentis |
| Dados | **ISO 8601** | datas/horas (`2026-09-16`, instantes UTC `...Z`) |
| API | **RFC 9457** (Problem Details), OpenAPI 3.1 | erros estruturados `application/problem+json` |
| HTTP | RFC 9110/9111 | ETag/If-Match para concorrência otimista |
| Commits | **Conventional Commits 1.0** | changelog gerado (git-cliff), releases |
| Versionamento | **SemVer 2.0** | tags `v1.2.3` |
| Arquitetura | **DDD** (Evans/Vernon), **FSD** (feature-sliced.design) | ver §5 |
| Decisões | **ADRs** (Michael Nygard) | `docs/adr/NNNN-*.md` |
| Operação | **12-Factor App**, **OWASP API Security Top 10**, **ASVS 4.0** (alvo L2) | config por env, segurança |
| A11y | **WCAG 2.2 AA**, WAI-ARIA APG | foco visível, teclado no drag-and-drop |
| Testes | pirâmide clássica (Cohn) + property-based testing | ver §8 |

### 4.2 Glossário canônico

| Termo | Definição no produto |
|---|---|
| Workspace | espaço isolado (tenant) que contém projetos, membros e integrações |
| Projeto | conjunto de quadros/backlog de um produto ou time |
| Board | visão Kanban de um projeto; colunas mapeiam para 3 categorias de status |
| Categoria de status | `TODO`, `IN_PROGRESS`, `DONE` (convenção Jira StatusCategory) |
| Work Item | unidade de trabalho; tipo ∈ {`EPIC`, `STORY`, `TASK`, `BUG`, `SUBTASK`} |
| Sprint | timebox de 1–4 semanas com objetivo (Sprint Goal) e datas fixas |
| Backlog | itens sem sprint atribuída (Product Backlog) |
| Evento de domínio | registro imutável de uma mudança de estado de um work item/sprint |
| Definition of Done (DoD) | item só conta como concluído quando está em coluna de categoria `DONE` |
| Velocidade | pontos (ou itens) concluídos por sprint, média móvel de 3 sprints |
| Escopo da sprint | itens vinculados à sprint em um instante do tempo (pode mudar — e aparece no gráfico) |

### 4.3 Regras de negócio normativas (`RN-*`)

**Identidade e tenancy**
- `RN-01` — Todo workspace tem exatamente ≥1 membro com papel `OWNER`. Papéis: `OWNER`, `ADMIN`, `MEMBER`, `VIEWER`.
- `RN-02` — Todas as leituras/escritas são escopadas por `workspace_id`; membro só acessa workspaces em que participa. Violação = 404 (não 403), para não vazar existência.
- `RN-03` — Convites: token de uso único, expira em 7 dias; reenvio revoga o anterior.
- `RN-04` — Senha: mínimo 10 caracteres, hash Argon2id; nunca logada, nunca retornada por API.

**Projetos e board**
- `RN-05` — Nome de projeto único por workspace (case-insensitive, com trim).
- `RN-06` — Todo board tem ≥1 coluna; toda coluna mapeia exatamente 1 categoria; ≥1 coluna por categoria. Coluna `DONE` implícita no fluxo.
- `RN-07` — Itens do board pertencem a exatamente 1 projeto; tipos `SUBTASK` perdem pontos para contagem (config: pontos contam só no nível pai).

**Work items**
- `RN-08` — Título obrigatório (1–200 chars). Descrição em Markdown sanitizado.
- `RN-09` — Hierarquia: `EPIC` não tem pai e não pode ser subtarefa; `SUBTASK` exige pai (`STORY|TASK|BUG`); profundidade máxima 2 níveis abaixo da Epic (igual Jira).
- `RN-10` — Story points apenas no conjunto Fibonacci `{1,2,3,5,8,13}`; itens sem estimativa contam como "sem estimativa" (nunca como 0 em gráficos de pontos; aparecem em contagem separada).
- `RN-11` — Um item pertence a no máximo 1 sprint por vez e a no máximo 1 projeto.
- `RN-12` — Transições de status liberadas, porém toda transição gera evento; sair de `DONE` gera evento `reopened` e reabre o item no burndown do dia (sem efeito retroativo).
- `RN-13` — WIP limit por coluna: exceder gera alerta (padrão) ou bloqueio (config `wip_enforcement=soft|hard`).

**Sprints**
- `RN-14` — Duração 7–28 dias (1–4 semanas, Scrum Guide); `end_date > start_date`.
- `RN-15` — No máximo 1 sprint `ACTIVE` por board.
- `RN-16` — Iniciar sprint exige: Sprint Goal (1 frase, ≤280 chars), ≥1 item e ausência de sprint ativa.
- `RN-17` — Sprint concluída é imutável: itens não concluídos são movidos para o backlog ou próxima sprint via evento `carried_over` (nunca por mutação do histórico).
- `RN-18` — Datas de sprint são `DATE` no timezone do workspace; instantes de eventos são UTC.

**Integrações**
- `RN-19` — Campos sob propriedade do Jira (`points`, `status`, `assignee`, `sprint`) não são editáveis localmente enquanto o vínculo estiver ativo; campos locais (`labels` internos, notas) permanecem editáveis.
- `RN-20` — Ingestão idempotente: chave única `(source, external_event_id)`; reentrega de webhook não duplica evento.
- `RN-21` — Conectar integração exige papel `ADMIN+`; tokens são criptografados em repouso (AES-GCM/Fernet com chave em env) e nunca expostos ao cliente.
- `RN-22` — Desconectar integração mantém os itens importados (viram locais) ou os arquiva, conforme escolha explícita do usuário no fluxo.

**Auditoria e dados**
- `RN-23` — Toda mutação passa por caso de uso e appenda ≥1 evento com `actor_id`, `occurred_at` (UTC), `workspace_id`, `source` (`local|jira`).
- `RN-24` — Exclusão é soft (`archived_at`); hard delete apenas em purge de workspace (LGPD — direito ao esquecimento, cascata completa).
- `RN-25` — Event log é append-only: nunca `UPDATE`/`DELETE` em `domain_events` (garantido por permissões de DB + teste de integração).

### 4.4 Regras de métricas normativas (`RM-*`)

Burndown correto é o coração do produto; a especificação abaixo elimina as ambiguidades do código atual.

- `RM-01` — **Eixo temporal**: dias úteis do workspace (seg–sex por padrão; feriados opcionais por workspace). O dia do sprint `D0..DN` é delimitado à meia-noite local do workspace. Armazenamento sempre UTC; cálculo no timezone do workspace.
- `RM-02` — **Escopo(t)** = Σ pontos dos itens vinculados à sprint no instante `t` (e não apagados). Mudança de escopo é evento, não reescrita; o gráfico mostra degrau visível no dia do evento.
- `RM-03` — **Concluído(t)** = Σ pontos dos itens que estavam em categoria `DONE` ao fim do dia `t` (conta o instante do evento `status_changed → DONE`, nunca a data de criação).
- `RM-04` — **Restante(t)** = Escopo(t) − Concluído(t). Nunca negativo (invariante testada).
- `RM-05` — **Linha ideal**: linear de `Restante(D0)` até `0` em `DN` (último dia do sprint), por dia útil: `ideal(i) = escopo_inicial × (1 − i/N)`. Modo alternativo "ideal por velocity" (inclinação = velocity média / duração) fica como configuração futura.
- `RM-06` — **Burndown congela** ao fim da sprint (snapshot imutável). Recálculo via replay do event log é possível, mas exibido como "revisão", nunca sobrescrevendo o snapshot.
- `RM-07` — **Burnup** = Concluído(t) acumulado + linha de Escopo(t), evidenciando *scope creep*.
- `RM-08` — **Velocity(sprint)** = Σ pontos (ou itens) `DONE` cujo `done_at ∈ [start, end]` da sprint. Reportar: valor da sprint, **média móvel das últimas 3**, planejado vs. entregue.
- `RM-09` — **Throughput** = itens `DONE` por semana (janela móvel de 4 semanas).
- `RM-10` — **Cycle time** = `done_at − primeiro_in_progress_at`; **Lead time** = `done_at − created_at`. Reportar sempre **p50, p85 e p95** (percentis, não média — convenção Kanban/flow metrics).
- `RM-11` — **CFD (Cumulative Flow Diagram)** = contagem de itens por categoria de status ao fim de cada dia útil.
- `RM-12` — Itens `DONE` em sprints fechadas nunca são rencontados em sprints futuras, mesmo em carryover (o carryover cria novo vínculo de sprint).
- `RM-13` — Em gráficos de **pontos**, itens sem estimativa são excluídos e reportados à parte ("n sem estimativa"). Em gráficos de **contagem**, todos entram.
- `RM-14` — Snapshot diário de métricas é idempotente por `(sprint_id, date)`; cron roda 1x/dia e reprocessa dias ausentes (self-healing).
- `RM-15` — Anti-padrões explicitamente barrados pelo produto: atualizar burndown retroativamente; usar dias corridos no lugar de dias úteis; alterar story points de item no meio da sprint sem evento visível; contar subtarefas junto com a história pai no mesmo total.

### 4.5 Convenções de engenharia

- **Commits**: Conventional Commits (`feat|fix|refactor|docs|test|chore|perf|ci|build|security`), escopo = bounded context ou app (`feat(work): ...`, `fix(metrics): ...`).
- **Branches**: trunk-based, branches curtas `feat/<slug>`, `fix/<slug>`; PR obrigatório com preview deploy; squash merge; CI verde é pré-requisito.
- **ADR**: toda decisão arquitetural relevante vira ADR numerada; PRs que mudam contrato de API exigem ADR ou RFC.
- **API**: REST `/api/v1`, substantivos plurais, JSON `snake_case`, paginação por cursor (`?limit&cursor`), ordenação `?sort=-created_at`, filtros por campo, ETag/If-Match para edição concorrente de itens (409 em versão obsoleta), `Idempotency-Key` em POSTs de risco.
- **Erros**: RFC 9457 (`type`, `title`, `status`, `detail`, `instance`, `code`), com `code` de negócio estável (ex.: `SPRINT_ALREADY_ACTIVE`) para o front traduzir — API nunca retorna texto traduzido.
- **Frontend**: mensagens i18n sempre por chave; nenhuma string hardcoded em componente; datas/formatos via `Intl`.

---

## 5. Arquitetura alvo

### 5.1 Visão macro

```
┌──────────────────────────── Vercel ────────────────────────────┐
│                                                                │
│  apps/web (Vite SPA, CDN)          apps/api (FastAPI, Python)  │
│  ┌───────────────────────┐         ┌────────────────────────┐  │
│  │ FSD: app/pages/       │  HTTPS  │ interface (routers)    │  │
│  │ widgets/features/     │ ──────► │ application (use cases)│  │
│  │ entities/shared       │  OpenAPI│ domain (agregados)     │  │
│  └───────────────────────┘         │ infra (SQLAlchemy,     │  │
│                                    │        Jira client)    │  │
│                                    └───────────┬────────────┘  │
└────────────────────────────────────────────────┼───────────────┘
                                                 │ asyncpg (pooler)
                                    ┌────────────▼────────────┐
                                    │  Neon Postgres (free)   │    ┌─────────────┐
                                    │  event log + read models│◄───│ Jira Cloud  │
                                    └─────────────────────────┘    │ OAuth 3LO + │
                                                                   │  webhooks   │
                                                                   └─────────────┘
```

**Bounded contexts** (monolito modular — um deploy, fronteiras fortes):

| Contexto | Responsabilidade | Depende de |
|---|---|---|
| `identity` | users, organizations, workspaces, memberships, convites, sessões | shared |
| `work` | projects, boards, colunas, work items, sprints, backlog, WIP | identity (só IDs), shared |
| `metrics` | read models derivados do event log: burndown, burnup, velocity, CFD, cycle/lead | work (eventos), shared |
| `integrations` | conexões Jira (OAuth), mapeamentos, sync, webhooks, idempotência | work (comandos via use cases), identity |
| `platform` | infra transversal: db, event bus, outbox, config, logging, auth middleware | — |
| `shared` | kernel: Entity, AggregateRoot, DomainEvent, ValueObject, Result/errors, Clock, IDs | — |

Regra de ouro: **contextos não importam as tripas uns dos outros** — comunicação por casos de uso e eventos de domínio. Fronteiras são *enforced* por `import-linter` (contratos de camadas) no CI.

### 5.2 Layout do monorepo

```
agile-tracker/
├── apps/
│   ├── web/                          # React + Vite + TS
│   └── api/                          # FastAPI (Python)
├── packages/
│   ├── api-client/                   # tipos TS gerados do OpenAPI + client
│   ├── ui/                           # design system "Ink" + primitivos shadcn
│   ├── tsconfig/                     # tsconfigs compartilhados (base, react, node)
│   ├── eslint-config/                # flat config compartilhada
│   └── i18n/                         # mensagens pt-BR/en tipadas
├── infra/
│   ├── docker/                       # Dockerfile.api (portabilidade/fuga da Vercel)
│   └── scripts/                      # seed, migrate, export legado
├── docs/
│   ├── PLANO-REVAMP.md               # este documento
│   ├── adr/                          # decisões arquiteturais
│   ├── domain/                       # glossário + catálogo RN/RM (gerado do código)
│   └── runbook/                      # operação, incidentes, backups
├── .github/
│   ├── workflows/                    # ci.yml, deploy, nightly
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── biome.json                        # formato + lint base (JS/TS)
├── eslint.config.mjs                 # lint profundo type-aware
├── pnpm-workspace.yaml
├── turbo.json
├── package.json                      # scripts raiz (turbo)
├── commitlint.config.mjs
├── .gitleaks.toml
└── README.md
```

**Gerenciadores**: `pnpm` workspaces no lado JS (Turborepo foi avaliado e removido — ver ADR 0001); `uv` (lockfile `uv.lock`) no lado Python. Comandos cross-platform (Windows-friendly) via scripts pnpm.

### 5.3 Backend — monolito modular + DDD

```
apps/api/
├── src/agile_tracker/
│   ├── main.py                        # app factory + middlewares + routers
│   ├── shared/                        # kernel
│   │   ├── domain.py                  # Entity, AggregateRoot, DomainEvent, ValueObject
│   │   ├── result.py                  # Result/Either + errors de domínio
│   │   ├── clock.py                   # Clock injetável (Freezegun/time-machine nos testes)
│   │   └── ids.py                     # UUIDv7 (ordenável por tempo)
│   ├── identity/
│   │   ├── domain/{entities.py,value_objects.py,services.py,events.py,repositories.py,errors.py}
│   │   ├── application/{use_cases/,ports.py,dto.py}
│   │   ├── infrastructure/{orm/,repositories/,security/{argon2,jwt}.py}
│   │   └── interface/{router.py,schemas.py,deps.py}
│   ├── work/
│   │   ├── domain/{project.py,board.py,work_item.py,sprint.py,policies.py,events.py,repositories.py,errors.py}
│   │   ├── application/{use_cases/,dto.py,ports.py}
│   │   ├── infrastructure/{orm/,repositories/}
│   │   └── interface/{routers/{projects,boards,items,sprints,backlog}.py,schemas.py}
│   ├── metrics/
│   │   ├── domain/{calculators.py,policies.py}      # funções puras, 100% testáveis
│   │   ├── application/{queries.py,projectors.py}   # projeções do event log
│   │   ├── infrastructure/{orm/,queries_sql.py}
│   │   └── interface/{router.py,schemas.py}
│   ├── integrations/
│   │   ├── domain/{connection.py,mapping.py,events.py}
│   │   ├── application/{connect_jira.py,import_project.py,handle_webhook.py,reconcile.py}
│   │   ├── infrastructure/{jira/{client.py,oauth.py,fields.py},token_vault.py,webhook_verify.py}
│   │   └── interface/{router.py,webhook_router.py}
│   └── platform/{config.py,db.py,event_bus.py,outbox.py,logging.py,middleware/,security.py,health.py}
├── migrations/                        # Alembic (autogenerate proibido em prod; revisão revisada)
├── tests/
│   ├── unit/<context>/                # domínio puro + use cases com fakes
│   ├── integration/                   # repositórios (Testcontainers Postgres), RLS de tenant
│   └── e2e/                           # fluxos completos via API (httpx)
└── pyproject.toml                     # uv, ruff, mypy, pytest config
```

**Padrões internos:**
- **Agregados** com invariantes no construtor/fábrica (`Sprint.start()` valida `RN-14..16`) e eventos levantados (`SprintStarted`, `WorkItemMoved`, `StoryPointsChanged`...).
- **Value Objects**: `StoryPoints` (só Fibonacci), `SprintState` (PLANNED/ACTIVE/COMPLETED), `StatusCategory`, `WorkItemKey` (`PROJ-123`).
- **Event log append-only** (`domain_events`): `id, workspace_id, aggregate_type, aggregate_id, type, payload jsonb, actor_id, source, external_event_id (nullable), occurred_at, recorded_at`. É a fonte de verdade para métricas e auditoria.
- **Projeções**: síncronas na transação (dados pequenos) + cron noturno de reconciliação/replay; `outbox` para efeitos externos (webhooks de saída, notificações futuras).
- **Repositórios** por agregado; **Unit of Work** por request (sessão SQLAlchemy async).
- **Use cases** finos: 1 caso de uso = 1 intenção de negócio; interface HTTP só traduz DTO ↔ use case (sem regra na rota).
- **Tenant scoping**: `workspace_id` obrigatório em toda query; teste de integração garante isolamento cruzado (`RN-02`).
- **Concorrência**: coluna `version` (optimistic lock) em work items → envio de `If-Match`/`version`; 409 com problem detail.

**Stack Python:**

| Item | Escolha | Nota |
|---|---|---|
| Runtime | Python 3.12+ | validar suporte do runtime Vercel na Fase 0 |
| Gestão | `uv` (lockfile) | rápido, padrão moderno |
| Framework | FastAPI + Pydantic v2 | OpenAPI automático, docs em `/docs` |
| ORM | SQLAlchemy 2 async + `asyncpg` | com `NullPool` + `statement_cache_size=0` (pgbouncer do Neon) |
| Migrations | Alembic | rodadas no CI a cada merge em `main` |
| Serverless | `mangum` (`handler = Mangum(app)`) | em `api/index.py` do runtime Vercel |
| Lint/format | Ruff (E,F,W,I,N,UP,B,C4,SIM,S,C4,PT,RUF,ARG,TID,ANN no domínio) | `S` = regras de segurança (bandit-like) |
| Tipos | mypy `strict` no domínio/aplicação; padrão no infra | |
| Arquitetura | `import-linter` | contratos: domínio ↛ infra; contextos isolados |
| Testes | pytest, pytest-asyncio, httpx, testcontainers, hypothesis, time-machine, factory-boy | ver §8 |

### 5.4 Frontend — FSD + stack

**Stack:**

| Item | Escolha | Nota |
|---|---|---|
| Build | Vite 7 + React 19 + TS 5.9 (`strict`) | SPA estática na Vercel |
| Estilo | Tailwind v4 (CSS-first `@theme inline`) + **shadcn/ui** | mesmo preset do portfólio (neutral/base-vega, CSS vars) |
| Design tokens | sistema "Ink" do portfólio (ver §6) | portado para `packages/ui` |
| Router | React Router v7 (library mode) | rotas aninhadas + loaders onde fizer sentido |
| Server state | TanStack Query v5 | cache, optimistic updates, `refetchInterval` (substitui WebSocket) |
| Forms | react-hook-form + Zod v4 | mesmos schemas em `packages/api-client` quando possível |
| Drag & drop | `@dnd-kit` | sensors de teclado obrigatórios (a11y) |
| Charts | Recharts (via wrapper shadcn `chart`) | linha ideal tracejada, gradientes sutis |
| Datas | date-fns + `Intl` | timezone do workspace na apresentação |
| i18n | i18next + react-i18next | pt-BR default, en; chaves tipadas |
| Ícones | lucide-react (permitido) + set desenhado para o shell | consistência com o portfólio |
| Estado cliente | quase nenhum; `zustand` só se drag global exigir | YAGNI |

**Árvore FSD (`apps/web/src`):**

```
src/
├── app/                    # entry, providers (Query, i18n, theme, router), estilos globais
├── pages/                  # 1 rota = 1 slice
│   ├── login/  register/  onboarding/
│   ├── board/  backlog/  sprints/  metrics/  settings/  members/  integrations/  demo/
├── widgets/
│   ├── app-shell/          # TopBar 64px, rail de navegação, progress bar
│   ├── kanban-board/       # colunas + drag ctx
│   ├── backlog-ledger/     # lista ledger estilo portfólio
│   ├── sprint-header/      # goal, datas, dias restantes, status "live"
│   ├── burndown-panel/  velocity-panel/  cfd-panel/
│   └── team-info/
├── features/
│   ├── auth/               # login-form, register-form, session-guard
│   ├── create-work-item/  edit-work-item/  move-work-item/
│   ├── plan-sprint/  start-sprint/  complete-sprint/
│   ├── connect-jira/  import-jira-project/  configure-field-mapping/
│   ├── switch-theme/  switch-language/
│   └── invite-member/  manage-roles/
├── entities/
│   ├── work-item/{ui,model,api,lib}
│   ├── sprint/  board/  project/  member/  metric/  integration/
└── shared/
    ├── ui/                 # re-export do packages/ui (shadcn customizado)
    ├── api/                # client gerado, hooks base, erros RFC 9457 → i18n
    ├── lib/                # datas, formatação, hooks utilitários
    ├── config/             # env, constantes, feature flags
    ├── i18n/               # setup i18next + re-export de packages/i18n
    └── assets/
```

**Regras FSD (enforced por `dependency-cruiser` no CI):**
- Camadas só importam de camadas inferiores: `app → pages → widgets → features → entities → shared`.
- Slices da mesma camada **não** se importam entre si.
- Cross-imports públicos apenas via `index.ts` do slice (`@/entities/work-item`), nunca paths internos.
- ESLint rule para proibir `shared` importando de camadas superiores.

**Contratos front ↔ back:**
1. FastAPI gera `openapi.json` no CI.
2. Job `contract` roda `openapi-typescript` → `packages/api-client/src/schema.d.ts`; se houver diff não commitado, CI falha (contrato sempre sincronizado).
3. `openapi-fetch` + hooks TanStack Query tipados; erros mapeados para `ProblemDetails` e traduzidos por `code` (`shared/api/errors.ts`).

### 5.5 Modelo de dados (Neon Postgres)

Tabelas principais (todas com `workspace_id`, timestamps UTC, UUIDv7):

```
users(id, email uniq, password_hash, name, locale, created_at, ...)
organizations(id, name, slug uniq, ...)
workspaces(id, org_id, name, slug, timezone, working_days bitmask, ...)
memberships(id, workspace_id, user_id, role, ...) uniq(workspace_id,user_id)
invites(id, workspace_id, email, role, token_hash, expires_at, ...)
refresh_tokens(id, user_id, token_hash, family_id, expires_at, revoked_at, ...)

projects(id, workspace_id, name, key uniq/workspace, mode[POINTS|COUNT], wip_enforcement, ...)
boards(id, project_id, name, ...)
board_columns(id, board_id, name, position, category[TODO|IN_PROGRESS|DONE], wip_limit, ...)
work_items(id, project_id, parent_id, sprint_id, type, key uniq/project, title, description,
           status_column_id, story_points, priority, assignee_id, due_date,
           created_at, done_at, first_in_progress_at, archived_at, version, ...)
sprint_assignments(id, work_item_id, sprint_id, added_at, removed_at)   # histórico de vínculo
sprints(id, board_id, name, goal, state, start_date, end_date, completed_at, ...)
labels / work_item_labels
comments(id, work_item_id, author_id, body, ...)

domain_events(id, workspace_id, aggregate_type, aggregate_id, type, payload jsonb,
              actor_id, source[local|jira], external_event_id, occurred_at, recorded_at)
              # append-only; uniq(source, external_event_id) where not null
outbox(id, event_id, topic, payload, available_at, processed_at, attempts)
projection_state(projection, last_event_id)                     # watermarks
metric_snapshots(id, workspace_id, sprint_id, date, payload jsonb, uniq(sprint_id,date))

integrations(id, workspace_id, provider[JIRA], cloud_id, status, ...)
integration_tokens(id, integration_id, refresh_token_enc, access_token_enc, expires_at)
external_mappings(id, integration_id, entity_type, external_id, internal_id, field_map jsonb)
sync_jobs(id, integration_id, type, cursor jsonb, state, last_error, ...)
webhook_events(id, integration_id, external_event_id, received_at, payload) uniq(integration,external)
```

**Neon + serverless:** usar endpoint **pooled** (`*-pooler`), `NullPool` no SQLAlchemy, desabilitar prepared statements no asyncpg, `pool_pre_ping`. Migrations rodam no CI (nunca no cold start da função). Branches da Neon: `main` (prod), `dev`, e branch efêmera por PR (recurso nativo "branch per PR" com GitHub Actions).

### 5.6 Integração Jira (desenho)

1. **Conectar**: `GET /api/v1/integrations/jira/authorize` → redireciona para `auth.atlassian.com/authorize` (scopes: `read:jira-work`, `write:jira-work`, `read:jira-user`, `offline_access`, `manage:jira-webhook` — validar lista final na implementação). Callback troca `code` por tokens, consulta `accessible-resources`, usuário escolhe o site → cria `integration` + tokens criptografados; estado anti-CSRF + PKCE.
2. **Descoberta de campos**: story points (`customfield_10016` etc.) e sprint (`customfield_10020`) variam por instância → tela de mapeamento com sugestões automáticas e detecção de tipos.
3. **Import** (resumível e em chunks): escolhe projeto/board → cria entidades espelhadas via **casos de uso do contexto `work`** (nunca SQL direto) → `sync_jobs.cursor` permite retomar; paginação `startAt/maxResults`; respeita timeout serverless com chunks acionados pelo front (progresso via polling).
4. **Webhooks dinâmicos**: registro via REST (`jira:issue_created`, `jira:issue_updated`, `jira:issue_deleted`, `sprint_started`, `sprint_closed`); endpoint público com segredo no path + validação quando disponível + idempotência (`webhook_events`); resposta 2xx rápida e processamento do evento na mesma request (payload pequeno) ou enfileirado.
5. **Reconciliação noturna**: cron compara `updated` do Jira × estado local no período e corrige drift (self-healing), além de renovar webhooks antes da expiração.
6. **Rate limiting**: backoff exponencial + `Retry-After`; limites por conexão.
7. **Fuso horário**: Jira retorna ISO 8601 com offset; normalizar para UTC no evento e resolver "dia do sprint" no timezone do workspace.

### 5.7 Deploy (Vercel + Neon, plano free)

| Peça | Onde | Config |
|---|---|---|
| `apps/web` | Vercel (projeto 1) | build estático Vite; rewrite SPA para `index.html` |
| `apps/api` | Vercel (projeto 2) | runtime Python, `api/index.py` com Mangum; envs: `DATABASE_URL`, `JWT_SECRET`, `INTEGRATION_SECRET_KEY`, `JIRA_CLIENT_ID/SECRET` |
| Banco | Neon free | branch `main` + pooled endpoint; branch-per-PR para previews |
| Cron | Vercel Cron | Hobby: 2 jobs/dia → 1 job noturno unificado (snapshots métricas + reconcile Jira + renovação de webhook) |
| Preview | Vercel Preview | por PR, apontando para branch Neon efêmera |

**Limitações conhecidas do alvo free (mitigações no design):**
- Sem WebSocket em functions → UI usa polling adaptativo (`refetchInterval` 15–30s em board, 60s em métricas) + “última sincronização” visível. Se realtime virar requisito, migração para Fly.io/Render com ASGI contínuo é viável sem mudar código (imagem Docker pronta em `infra/docker`).
- Timeout de função (10s padrão) → imports e reconcile em chunks resumíveis; nada de operação longa síncrona.
- Limite de payload (4.5MB) → import sempre paginado.
- Cold start → Neon + function aquecida no cron; endpoints enxutos; medir.
- Cron 1x/dia no Hobby → snapshots noturnos cobrem dias ausentes (`RM-14`); webhooks cobrem o tempo real.

---

## 6. Design system — "Ink" aplicado ao produto

Portado do portfólio (obra-prima do autor), com ajustes de aplicação (mais densidade, tabelas, formulários, board).

### 6.1 Tokens (fonte: portfólio `globals.css`)

| Token | Light | Dark | Uso no produto |
|---|---|---|---|
| `--paper` | `#FBFBF9` | `#0D0D0C` | fundo de página/superfícies |
| `--ink` | `#0D0D0C` | `#F4F3EF` | texto, réguas 2px, invertidos |
| `--ash` | `#75736D` | `#918E86` | texto secundário, labels mono |
| `--rule` | `#DFDDD6` | `#2B2B27` | hairline 1px (bordas, separadores) |
| `--gold` | `#8A6B00` | `#F3CA4D` | **status vivo**: sprint ativa, WIP estourado, "Resultado" |
| `--gold-fill` | `#F3CA4D` | `#F3CA4D` | ponto de status 7x7 |
| `--hover-bg` | `#F5F4F0` | `#171715` | hover de linha/card |
| `--ease` | `cubic-bezier(.76,0,.24,1)` | idem | hovers, bordas |
| `--soft` | `cubic-bezier(.16,1,.3,1)` | idem | reveals, animações |

**Princípios herdados (inegociáveis):**
- Zero gradientes, zero sombras, raio 0 (exceto pílulas de CTA 999px).
- **Tipografia carrega a interface**: Archivo (eixo `wdth` 112, 125 em títulos grandes; line-height .86; tracking −.045em) + Martian Mono (labels `.62rem`, uppercase, tracking `.14em`).
- **Ouro racionado**: só para status vivo e resultado — nunca decoração.
- Foco visível `outline: 2px solid var(--ink); offset 3px` (WCAG 2.2 AA).
- Dark mode por `data-theme` + script pré-paint (anti-flash), wipe circular via View Transitions no toggle (como o portfólio).
- `prefers-reduced-motion` desliga tudo.

### 6.2 Mapeamento shadcn ↔ Ink

`--background/--card/--popover → --paper`; `--foreground → --ink`; `--muted/--accent → --hover-bg`; `--muted-foreground → --ash`; `--primary → --ink` e `--primary-foreground → --paper`; `--border/--input → --rule`; `--ring → --ink`; `--radius: 0` (usar `rounded-full` só em CTA pílula). Erros usam um vermelho dessaturado dedicado (`--danger: #A33A2E` light / `#E08A7D` dark), reservado a falhas — nunca em chrome. Componentes shadcn são reestilizados em `packages/ui` (button “pill” e “plain”, dialog quadrado com borda 1px, tooltip paper + régua, select/input com underline 1px estilo ledger).

### 6.3 Linguagem de interface do produto

- **App shell**: TopBar fixa 64px (mark 34x34 "AT" ink, workspace switcher, nav em `.roll`, `seg` PT/EN, toggle tema `.sq`); rail lateral opcional com labels mono + régua vertical; conteúdo em `.shell` (max 96rem, padding `clamp(1.25rem,3vw,3rem)`).
- **Kanban**: colunas com régua superior 2px ink + label mono uppercase + contador tabular; WIP `3/5` em ash, excedido em ouro; cards = superfície paper com borda 1px rule (raio 0), hover `--hover-bg`, arrastando = borda ink; tipo do item em mono 11px; pontos à direita em mono/tabular; avatar 24x24 quadrado com iniciais; labels como tags 1px rule (sem pill).
- **Backlog**: ledger `.led` (data/tipo à esquerda em mono, título Archivo, pontos à direita), expansão inline, seleção múltipla com checkbox quadrado custom, drag para sprint com indicador de posição em ouro.
- **Sprint header**: kicker mono "Sprint 14 · ACTIVE" com ponto ouro quando ativa; goal em `.lede`; datas ISO em mono; "dias restantes" com tabular-nums; barra de progresso 2px full-width (como a scroll progress do portfólio).
- **Métricas**: sem "cards de dashboard"; layout editorial: seção burndown (gráfico grande), ledger de números (velocity média p50 etc.) com réguas, CFD como stacked area monocromático + ouro para Done, cycle/lead time com percentis em ledger. Tooltips paper + régua + mono.
- **Charts (Recharts)**: Restante = ink sólido 2px; Ideal = ash tracejado `[4,4]`; Concluído/burnup = ouro; grid horizontal 1px `--rule`; eixos mono `.62rem` ash; marcos de mudança de escopo = ponto ouro + tooltip. Altura `clamp(320px, 40vh, 480px)`.
- **Formulários**: shadcn + RHF/Zod; labels mono uppercase; inputs com borda 1px rule e foco ink; erros com `--danger` + texto auxiliar; diálogos quadrados.
- **i18n**: PT/EN com cross-fade (View Transition) reaproveitado do portfólio; `<html lang>` sincronizado; datas/números por `Intl`; nenhum texto da API traduzido no servidor.

### 6.4 A11y (alvo AA)

- Drag-and-drop 100% operável por teclado (dnd-kit `KeyboardSensor` + anúncios `aria-live`).
- Navegação por tab em ordem lógica; skip-link; landmark roles.
- Contraste verificado (`--gold` light sobre paper = uso apenas em texto grande/dot com rótulo).
- `axe-core` no CI (componentes críticos + e2e).
- Touch targets ≥24px (herdado do portfólio).

---

## 7. Ferramentas, linters e qualidade

### 7.1 Divisão Biome × ESLint (frontend)

| Ferramenta | Papel | Config |
|---|---|---|
| **Biome** | formatação + lint base + organize imports (rápido, pre-commit/IDE) | `biome.json` na raiz; 2 espaços, lineWidth 100, aspas duplas |
| **ESLint 9 (flat)** | regras profundas type-aware + plugins de domínio | `typescript-eslint` (strictTypeChecked), `react-hooks`, `jsx-a11y`, `import-x`, `@vitest/eslint-plugin`, `eslint-plugin-playwright`, `eslint-plugin-boundaries` (FSD), regras anti-segredo |

Sem duplicação: Biome cuida do estilo e do básico; ESLint cuida do que exige tipos/plugins. Ambos rodam no CI; Biome também via `lint-staged` no pre-commit.

### 7.2 Python

- **Ruff** (`check` + `format`): E,F,W,I,N,UP,B,C4,SIM,S (segurança),PT (pytest),RUF,ARG,TID,ANN (domínio), com `line-length=100`.
- **mypy**: `strict` em `shared/`, `*/domain/`, `*/application/`; menos rígido em `infrastructure/`/`interface/`.
- **import-linter**: contratos de camadas e isolamento entre bounded contexts (falha o CI se violar).
- **pytest**: unit/integration/e2e + `pytest-cov` com thresholds; `hypothesis` para propriedades; `time-machine` para relógio.
- **pip-audit** e **gitleaks** no CI.

### 7.3 Git hooks e automação

- **husky + lint-staged**: staged JS/TS → `biome check --write`; staged `.py` → `ruff check --fix` + `ruff format`; mensagem de commit → `commitlint`.
- **PR template**: checklist (RN/RM afetadas, testes, ADR se contrato/arquitetura, i18n, a11y, segurança).
- **git-cliff**: changelog a partir de Conventional Commits.
- **Dependabot**: atualizações agrupadas (semanal) para npm e uv.

### 7.4 CI (GitHub Actions)

`ci.yml` com `paths-filter` (web/api/shared) para economizar minutos:

| Job | O que roda |
|---|---|
| `web-quality` | biome check, eslint, tsc --noEmit, dependency-cruiser (FSD), knip (dead code) |
| `web-test` | vitest run + coverage thresholds |
| `web-build` | vite build (artefato) |
| `api-quality` | ruff check/format --check, mypy, import-linter |
| `api-test` | pytest unit + integration (Postgres service) + coverage gates |
| `contract` | gera openapi.json → regenera api-client → falha se houver diff |
| `e2e` | Playwright contra preview (PR) / staging (main) |
| `security` | gitleaks, pip-audit, npm audit --audit-level=high |
| `deploy` | Neon migrate (Alembic) → deploy Vercel (via integração Git) |

**Gates de cobertura:** backend domínio ≥95%, global ≥85%; frontend `entities/features model` ≥90%, global ≥70%. Mutation testing (Stryker/mutmut) como job noturno opcional.

---

## 8. Estratégia de testes

### 8.1 Pirâmide (o que testar, onde)

| Camada | Ferramenta | Alvo | Exemplos obrigatórios |
|---|---|---|---|
| Unit domínio (back) | pytest | agregados/VOs/políticas, RMs | cada `RN-*` e `RM-*` com teste dedicado; calculadora de burndown com property-based |
| Unit aplicação (back) | pytest + fakes (repos in-memory) | use cases | start/close sprint, mover item, carryover, RBAC |
| Integração (back) | pytest + Testcontainers | repositórios, migrações, isolamento tenant, idempotência | workspace A não lê B; unique constraints; append-only do event log (UPDATE/DELETE falham) |
| API (back) | httpx AsyncClient | contratos HTTP, erros RFC 9457, auth/refresh rotation, rate limit, ETag/409 | snapshot do OpenAPI |
| Unit (front) | Vitest | `model/lib` puros | mapeadores de status, formatação de datas/tz, reducer do board |
| Componente (front) | Vitest + RTL + MSW | features/entities/widgets | KanbanCard, BacklogRow, BurndownPanel (estados loading/empty/error), LoginForm |
| E2E (front) | Playwright | fluxos críticos de ponta a ponta | (1) registro→workspace→projeto; (2) criar itens→sprint→iniciar→mover→concluir; (3) burndown reflete os eventos; (4) drag por teclado; (5) fluxo Jira com API mockada |
| A11y | axe-core (vitest + Playwright) | sem violações serious/critical | board, backlog, métricas, dialogs |
| Performance | Lighthouse CI (opcional) | ≥95 perf/a11y/best-practices na demo | budget de JS por rota |

### 8.2 Testes que garantem o coração do produto (métricas)

Property-based (`hypothesis`) para as calculadoras, provando invariantes de `RM-*`:

1. `Restante(t) ≥ 0` para qualquer sequência de eventos.
2. `ideal(0) = escopo_inicial` e `ideal(N) = 0`; `ideal` monotônica não-crescente.
3. `Concluído(t)` é não-decrescente (exceto eventos `reopened`, que o gráfico registra como degrau).
4. Evento em `t` altera o gráfico apenas em `t..N` — nunca antes de `t` (sem retroatividade invisível).
5. Replay do event log (fold) reproduz o estado atual e o snapshot congelado (determinismo).
6. Sublinhado por datasets "golden": seeds com resultados conferidos manualmente (planilha de referência) — o burndown exibido precisa bater ponto a ponto.

### 8.3 Dados e determinismo

- Factories (factory-boy / @faker-js/faker) com seed fixa; builders fluentes.
- Relógio injetável (`Clock` no domínio; `time-machine` nos testes); TZ dos testes fixa (`America/Sao_Paulo` e um caso `UTC`); nenhum teste depende de "hoje".
- E2E usa workspace demo seedado e browser timezone fixado; zero flakiness por data.
- Flaky policy: retries limitados só no E2E; teste flaky vira issue + quarentena imediata.

---

## 9. Segurança e privacidade

- **Auth**: Argon2id; access JWT curto (15 min) mantido em memória no front; refresh opaco (30 dias) em cookie `HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth`, rotação a cada uso com **reuse detection** (família revogada).
- **CSRF**: SameSite=Lax + exigência de header custom (`X-Requested-With`) nos endpoints de mutação que usam cookie + verificação de Origin.
- **Sessões**: revogação individual/global; logout apaga cookie e invalida família.
- **Tenant isolation**: `workspace_id` obrigatório (RN-02) + testes de integração cruzada; RLS do Postgres como defesa em profundidade (opcional, avaliar na Fase 6).
- **Rate limiting**: por IP e por usuário nos endpoints de auth (login, refresh, convite) e webhook; headers `Retry-After`. (Upstash Redis free ou tabela Postgres com janela — decidir na Fase 1.)
- **Segredos**: apenas em env da Vercel; `gitleaks` no CI; tokens Jira criptografados em repouso (AES-GCM/Fernet, chave `INTEGRATION_SECRET_KEY`), nunca retornados/expostos; logs com scrub de PII/token.
- **HTTP**: CORS restrito aos domínios web; CSP estrita (`default-src 'self'`), HSTS, `X-Content-Type-Options`, `Referrer-Policy`; docs OpenAPI expostas na demo (sem auth) mas com firewall de taxa.
- **OWASP API Top 10** endereçado: BOLA/BOPLA (RBAC + scoping), mass assignment (schemas explícitos), injection (ORM parametrizado + sanitização de Markdown), rate limit, error leakage (Problem Details sem stack).
- **LGPD**: minimização de dados; purge de workspace com cascata completa; política de retenção do event log (mínimo: vida do workspace); página de privacidade na demo.

---

## 10. Roadmap por fases

Estimativas em dev-days (part-time ~10-15h/semana). Cada fase termina com demo funcional e CI verde.

### Fase 0 — Fundação (3–5 dd)
Monorepo pnpm+turbo, `packages/*`, tsconfig/eslint/biome, uv+ruff+mypy+pytest, `import-linter`, CI mínima (lint+typecheck+unit+build), templates (PR/issue), commitlint+husky, gitleaks, ADR-0001..0008, projetos Vercel (web/api) + Neon (main/dev) + branch-per-PR, `/healthz`, deploy "hello" ponta a ponta, decisão do nome.
**Aceite:** PR abre preview na Vercel com web + api respondendo; CI verde; migrations rodam no CI; docs base publicados.

### Fase 1 — Identidade & Tenancy (5–8 dd)
Register/login/refresh/logout com rotação e rate limit; organizations/workspaces/memberships/invites; RBAC; telas login/registro/onboarding; shell do app (TopBar Ink, tema, i18n base).
**Aceite:** fluxo completo coberto por e2e; domínio ≥95% coberto; RN-01..04 testadas.

### Fase 2 — Work Management API (8–12 dd)
Projects, boards/colunas/categorias, work items + hierarquia, labels, assignees, backlog, sprints (planning→active→completed, carryover), transições com eventos, event log append-only, outbox, seed demo.
**Aceite:** RN-05..18 implementadas e testadas (1 teste por regra); OpenAPI estável; testes de integração de tenant/append-only verdes.

### Fase 3 — Frontend Kanban + Backlog (10–15 dd)
Páginas board/backlog/projetos/sprint planning; dnd-kit com teclado; optimistic updates; filtros; criação/edição de itens; seed demo navegável. **Dogfooding começa aqui** (usar o próprio app para acompanhar o revamp).
**Aceite:** e2e dos fluxos de board; axe sem serious/critical; dependency-cruiser sem violações FSD.

### Fase 4 — Métricas & Burndown real (8–12 dd)
Projeções a partir do event log; endpoints burndown/burnup/velocity/CFD/cycle-lead; snapshots diários + cron; UI de métricas estilo editorial; property tests das RMs; dataset golden conferido manualmente.
**Aceite:** burndown do seed bate ponto a ponto com planilha de referência; invariantes RM provadas; snapshot idempotente.

### Fase 5 — Integração Jira (10–15 dd)
OAuth 3LO + token vault; descoberta/mapeamento de campos; import resumível; webhooks + reconciliação noturna; UI de conexão/mapeamento/progresso; idempotência (RN-19..22); testes com fake Jira (respx).
**Aceite:** importar um projeto real do Jira Cloud; mudança no Jira refletida em <60s; reconcile noturno sem drift; conexão pode ser desfeita.

### Fase 6 — Hardening (5–8 dd)
Revisão OWASP, CSP/CORS, logs estruturados + Sentry (free), métricas de plataforma, e2e completo + a11y, Lighthouse budget, backups/export do Neon, runbook, testes de carga leves (k6 opcional), revisão de índices/query plans.
**Aceite:** ASVS L2 nos itens aplicáveis; p95 API <300ms (warm); runbook publicado.

### Fase 7 — Extensões ágeis (contínuo)
Forecasting Monte Carlo (throughput samples), notificações, export CSV/PDF, API pública com tokens, conector Trello (adaptador no contexto `integrations`), relatórios de sprint.

### Marco de portfólio (transversal)
Demo pública seedada, README bilíngue (PT/EN), case study no padrão do portfólio (problema → decisões → arquitetura → resultados), ADRs publicadas, changelog.

---

## 11. Riscos e mitigações

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Limites da Vercel free (timeout, sem WS, cron 1x/dia) | Alta | Médio | Design chunked/resumível, polling, cron unificado noturno; imagem Docker pronta para migrar para Fly/Render sem mudar código |
| Cold start / conexões Neon | Média | Médio | Pooler + `NullPool`, aquecimento via cron, queries enxutas, medir p95 desde a Fase 1 |
| OAuth 3LO: app em desenvolvimento e distribuição | Média | Baixo | Uso pessoal não exige review; se publicar para terceiros, planejar verificação Atlassian (Fase 7) |
| Complexidade FSD/DDD virar over-engineering | Média | Médio | Regra pragmática: só dividir quando doer; kernel mínimo; ADR para exceções; fronteiras automatizadas |
| Correção matemática do burndown | Baixa | Alto | Especificação RM normativa + property tests + golden dataset + replay |
| Scope creep (tracker vira produto infinito) | Alta | Médio | Fases com gates e "fora de escopo" explícito; releases utilizáveis desde a Fase 1 |
| Perda de dados (free tiers) | Baixa | Alto | `pg_dump` semanal para storage externo + PITR do Neon (verificar janela do plano) |
| Tempo solo + motivação | Média | Alto | Dogfooding cedo, fases curtas com demo, automação máxima, changelog visível |
| Jira `customfield` de points/sprint variam por instância | Certa | Médio | Descoberta automática + conferência do usuário no mapeamento (RN-19) |

---

## 12. Métricas de sucesso do revamp

- **Produto**: burndown do app conferido contra planilha/Jira com erro zero; workspace demo funcional; integração Jira real operando no dia a dia do autor.
- **Qualidade**: domínio ≥95% coberto; zero violação alta em linters de segurança; e2e e a11y verdes; zero `any`/dívida type-check.
- **Performance**: p95 API <300ms; TTI <2s na demo; Lighthouse ≥95.
- **Processo**: toda `RN-*`/`RM-*` rastreável até teste; ADRs atualizadas; PRs pequenos com preview.
- **Portfólio**: case study publicado + demo navegável sem login + README bilíngue.

---

## 13. Decisões em aberto (próximos passos)

1. Nome definitivo e criação do repositório monorepo (recomendação: novo repo; arquivar o antigo com README apontando).
2. Provedor de rate limiting (Upstash free × Postgres) — decidir na Fase 1.
3. Política de desconexão do Jira (manter itens como locais × arquivar) — decidir na Fase 5; a UI oferecerá escolha (RN-22).
4. Sentry × alternativa (GlitchTip self-host) — decidir na Fase 6.
5. Avaliar RLS do Postgres como defesa extra (Fase 6).

**Ação imediata sugerida:** aprovar este plano → Fase 0 (fundação do monorepo) → primeiro ADR: `0001-monorepo-modular-monolith`.

---

## Anexo A — ADRs iniciais a criar

| ADR | Título |
|---|---|
| 0001 | Monorepo com pnpm workspaces e monolito modular |
| 0002 | DDD com bounded contexts e event log append-only como fonte de métricas |
| 0003 | FSD no frontend + dependency-cruiser como guardião de fronteiras |
| 0004 | Design system "Ink" (Tailwind v4 + shadcn) e ouro racionado |
| 0005 | Biome + ESLint coexistindo: papéis separados |
| 0006 | JWT + refresh em cookie com rotação e reuse detection |
| 0007 | Alvo serverless Vercel + Neon e por que o código permanece portável (Docker) |
| 0008 | Jira Cloud via OAuth 2.0 3LO + webhooks + reconciliação |

## Anexo B — Mapa de rastreabilidade RN/RM → suíte de teste

| Origem | Suíte primária |
|---|---|
| RN-01..04 (identidade) | `tests/unit/identity`, `tests/e2e/auth` |
| RN-05..13 (projetos/board/itens) | `tests/unit/work`, `tests/integration/work` |
| RN-14..18 (sprints) | `tests/unit/work/test_sprint.py` |
| RN-19..22 (integrações) | `tests/unit/integrations`, `tests/e2e/jira` (fake) |
| RN-23..25 (auditoria) | `tests/integration/events` |
| RM-01..15 (métricas) | `tests/unit/metrics` (hypothesis + golden) |
| FSD/contratos | `dependency-cruiser`, job `contract`, e2e Playwright |
