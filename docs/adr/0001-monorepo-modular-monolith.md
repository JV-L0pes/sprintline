# ADR 0001 — Monorepo com monolito modular

- Status: aceito
- Data: 2026-09-16
- Contexto: projeto solo evoluindo de um app estático para uma plataforma de tracking ágil com backend próprio; tempo de desenvolvimento limitado e necessidade de portfólio técnico.

## Decisão

Adotar um monorepo (`pnpm` workspaces) com dois apps — `apps/web` (React/Vite) e `apps/api` (FastAPI) — e o backend como **monolito modular**: um único deploy, fronteiras de bounded context enforceadas por `import-linter` no CI.

> Nota (2026-09-17): o Turborepo foi removido. A Vercel o detectava no build via Git e substituía os comandos do projeto Python (`turbo run build`), quebrando a instalação das dependências; com um único app JS, o ganho de cache era marginal. Os scripts da raiz usam `pnpm --filter` diretamente.

## Consequências

- Um só checkout, CI unificado, lockfiles únicos por ecossistema.
- Extração futura de um contexto para serviço separado é mecânica (já não há imports profundos).
- Custo: disciplina para não furar fronteiras; mitigado por contratos automatizados.
- Backend permanece portável: imagem Docker própria, sem dependência exclusiva da Vercel.
