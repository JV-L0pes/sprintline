# Sprintline Web

SPA em React 19 + Vite + TypeScript, organizada em Feature-Sliced Design, com o design system **Ink** (Tailwind v4) herdado do portfólio: tipografia Archivo/Martian Mono, zero gradientes, raio 0 e o dourado racionado a sinal (status, marcador de seção, marca e foco).

## Scripts

```bash
pnpm dev        # Vite em :5173, com proxy /api -> http://localhost:8000
pnpm build      # tsc -b + vite build
pnpm typecheck  # tsc -b --noEmit
pnpm lint       # ESLint type-aware (react-hooks, jsx-a11y, playwright)
pnpm test:unit  # Vitest + Testing Library (35 testes)
pnpm test:e2e   # Playwright; precisa de CADENCIA_E2E=1 e do stack local (ver raiz)
```

Para o e2e, o Playwright sobe API + seed + web sozinho (`CADENCIA_E2E=1`); defina `UV_BIN` se o `uv` não estiver no PATH.

## Estrutura (FSD)

```
src/
  app/        bootstrap, rotas (lazy), estilos (globals.css + ink.css)
  pages/      home, projects, members, settings, board, backlog, metrics, ...
  widgets/    app-shell, kanban-board, backlog-ledger, sprints, painéis de métricas
  features/   auth, workspace, project, work-item, board-columns, sprint, members, integrations, shell
  entities/   session, workspace, project, board, work-item, sprint, metric, member, integration
  shared/     api (client/types/query), ui (button, dialog, select, input, misc, toast), i18n, lib
```

Regras de dependência: `pages → widgets → features → entities → shared` (nada de import invertido; o ESLint não cobre isso, mas o padrão é seguido à risca).

## Pontos de atenção

- **Select próprio** (`shared/ui/select.tsx`): listbox Ink com teclado, `aria-activedescendant` e flip inteligente (abre para baixo; só inverte sem espaço). Formulários usam `Controller` do react-hook-form.
- **i18n** (`shared/i18n/messages.ts`): pt-BR padrão + en; chaves estáveis e paridade garantida por teste; a API nunca devolve texto traduzido.
- **CSS**: `ink.css` não usa layers do Tailwind — regras de componente vencem utilitários (para larguras, envolva o controle num wrapper com `w-*`).
- **Proxy same-origin**: em produção o `vercel.json` reescreve `/api/*` para o projeto da API; `VITE_API_URL` fica vazio e os cookies de sessão continuam first-party.
