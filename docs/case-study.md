# Case study — Sprintline

> Da planilha estática à plataforma de tracking com métricas auditáveis.
> Autor: João Victor Lopes ([JV-L0pes](https://github.com/JV-L0pes)).

## O problema

O repositório original era um **gerador de burndown chart estático**: uma página que desenhava um gráfico a partir de dados mockados, com uma integração Trello **fictícia** (nomes de funções existiam, chamadas de rede não). Nada ali sobrevivia a um dia de uso real:

- as métricas eram pré-calculadas, não auditáveis — se o gráfico discordasse da realidade, não havia como saber quem estava errado;
- não existia conceito de workspace, projeto, sprint ou item — só arrays no front;
- não havia autenticação, tenancy ou qualquer noção de time.

O objetivo do revamp não era "arrumar o gráfico", e sim responder à pergunta que um time de verdade faz: **por que confiar neste número?** Burndown, velocity e cycle time só valem se forem reconstruíveis a partir de fatos imutáveis.

## O que foi construído

Uma plataforma de tracking ágil completa, em produção privada:

- **Kanban interno** estilo Jira, com colunas configuráveis (nome, WIP, ordem e categoria de status), itens hierárquicos, story points e backlog com drag-and-drop.
- **Sprints** segundo o Scrum Guide 2020 (objetivo, sprint ativa única, carryover explícito na conclusão).
- **Métricas derivadas do event log**: burndown, burnup, velocity, CFD e cycle/lead time com percentis.
- **Integrações reais**: Jira Cloud via OAuth 2.0 3LO (import idempotente + webhooks) e Trello (API key + autorização, boards/listas/cards mapeados e webhooks por board).
- **Multi-workspace** com papéis, convites por link, i18n pt-BR/en e ciclo de vida completo (arquivamento de itens/projetos, exclusão de workspace pelo owner).

## Decisões que definem o projeto

Cada decisão abaixo tem um ADR correspondente em `docs/adr/`.

1. **Event log append-only como fonte única das métricas** (ADR 0002). Nenhum contador denormalizado: todo movimento de item grava um evento com `from_category → to_category`. Burndown e velocity são reconstruídos por replay; se um número surpreende, dá para abrir o log e entender. A superfície de mutação fica isolada, e a auditoria sai de graça.
2. **Monolito modular com DDD, não microsserviços** (ADR 0001). Cinco contextos (`identity`, `work`, `metrics`, `integrations` + kernel `shared/platform`), com fronteiras **verificadas automaticamente** por `import-linter` (4 contratos) no CI. Complexidade de deploy de microsserviço sem o benefício — e as fronteiras que importam ficam explícitas.
3. **Métricas como calculadoras puras** (`metrics/domain/calculators.py`). Recebem séries e devolvem séries; sem banco, sem rede. Isso permite *golden dataset* conferido à mão + property tests com `hypothesis` (invariantes: escopo nunca negativo, burndown reconstrói a partir do log).
4. **Categoria de status separada do nome da coluna** (como no Jira). O time nomeia colunas como quiser ("Homologação", "Code review"); a categoria (To Do / In Progress / Done) é que diz o significado no fluxo — e é dela que as métricas dependem. O board exige ≥1 coluna por categoria, e reclassificar não pode esvaziar nenhuma.
5. **Arquivar versus excluir, decidido por caso**. Conteúdo (itens, projetos) usa *soft delete*: sai das listas, o histórico permanece. Workspace usa exclusão real em cascata, restrita ao owner — direito de eliminação (LGPD) de verdade, não um flag de "deletado".
6. **Privado por convite, sem demo pública** (ADR 0010). A instância é de uso pessoal: o modelo de ameaça muda, o registro aberto vira convite e o bootstrap do primeiro owner é um script operacional. Segurança decidida pelo modelo de uso, não por default de framework.
7. **Design system do portfólio reaproveitado no produto** (ADR 0004). O "Ink" (tipografia Archivo/Martian Mono, raio 0, zero sombra, dourado racionado a sinal) já existia; o produto fala a mesma língua visual. Menos invenção, mais coerência — e o polimento de UI vira decisão de sistema, não de tela.
8. **Vercel + Neon com proxy same-origin** (ADR 0007). O web reescreve `/api/*` para a API, então cookies de sessão continuam first-party em produção; migrações rodam no CI e nunca no cold start do serverless.

## Arquitetura

```
┌─────────────────────┐        ┌────────────────────────────────────────┐
│  SPA (React 19)     │ /api/* │  API única (FastAPI, ASGI serverless)  │
│  FSD + Ink + Query  ├───────►│  identity · work · metrics · integrations│
└─────────────────────┘        └──────────────┬─────────────────────────┘
                                              │ SQLAlchemy async
                                  ┌───────────▼───────────┐
                                  │  Postgres (Neon)      │
                                  │  domain_events (log)  │
                                  └───────────────────────┘
```

- **Frontend**: Feature-Sliced Design (`app → pages → widgets → features → entities → shared`), TanStack Query com optimistic updates no board, i18n pt-BR/en e um select listbox próprio (teclado, `aria-activedescendant`, flip inteligente).
- **Backend**: monolito modular com um agregado por contexto, casos de uso explícitos, repositórios sobre SQLAlchemy async e eventos de domínio persistidos na mesma transação.
- **Fatos do fluxo**: cada mutação relevante grava um evento append-only (`domain_events`) com ator, payload e timestamp UTC; as métricas leem exclusivamente dali.

## Qualidade e verificação

- **163 testes** (128 na API + 35 no web) + um e2e Playwright que roda o fluxo completo (registro → projeto → item → sprint → burndown) contra o stack real.
- CI com Postgres de verdade: lint, mypy strict, `import-linter`, suíte completa, **migrações aplicadas e revertidas** (`upgrade head` / `downgrade base` / `upgrade head`) e seed como smoke test.
- `gitleaks`, `pip-audit` e `pnpm audit` no pipeline de segurança.
- **51 regras de domínio catalogadas** (RN-01..36, RM-01..15), cada uma rastreada até o teste que a protege em `docs/domain/catalogo.md`.
- 10 ADRs documentando as decisões — inclusive as mudanças de rumo (Turborepo removido, entry ASGI nativo, Trello antecipado da Fase 7).

## Problemas interessantes resolvidos no caminho

- **asyncpg × Neon**: o parâmetro `sslmode` da URL do Neon não é aceito pelo driver; a URL é normalizada para `ssl` na camada de plataforma.
- **Vercel × Python**: a detecção automática de Turborepo quebrava o build da API (o passo de build passava a ignorar a instalação de dependências Python); a solução foi remover o Turbo do monorepo (nota no ADR 0001).
- **Rate limit × transação**: os contadores de tentativa precisam ser commitados **fora** da transação da request — senão o rollback de um 401 apagava justamente o que deveria contar.
- **Paridade de banco nos testes**: SQLite não força foreign keys por padrão; com `PRAGMA foreign_keys=ON` nos testes, os *cascades* se comportam como no Postgres e o CI pega bugs que antes só apareceriam em produção.

## Resultados

- O burndown do app confere com o próprio event log — a métrica é reconstruível, não decorada.
- A instância privada está em uso real (dogfooding), com integrações Jira/Trello operando por webhooks.
- Deploy contínuo com preview por PR; a API expõe OpenAPI e o catálogo de regras cobre o domínio.
- **Limitações assumidas**: snapshots diários via cron e reconciliação noturna ainda não implementados; notificações, export CSV/PDF, API pública com tokens e forecasting Monte Carlo ficam como próximos passos.

## Links

- [README](../README.md) · [Changelog](../CHANGELOG.md)
- [ADRs](adr/) · [Catálogo de regras](domain/catalogo.md) · [Runbook](runbook/operacao.md)
- [Plano do revamp](PLANO-REVAMP.md) (documento vivo da fase de planejamento)
