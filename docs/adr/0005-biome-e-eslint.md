# ADR 0005 — Biome + ESLint com papéis separados

- Status: aceito
- Data: 2026-09-16
- Contexto: Biome é rápido para formatação/base, mas o ecossistema de regras type-aware e plugins (react-hooks, jsx-a11y) vive no ESLint.

## Decisão

Biome formata, organiza imports e roda lint recomendado (com regras desativadas onde conflitam com decisões deste projeto, ex.: CSS com at-rules do Tailwind v4 é excluído do parser). ESLint 9 flat com `strictTypeChecked` cobre regras profundas de tipos, hooks, a11y e Playwright. Ambos rodam no CI; Biome também no pre-commit via lint-staged.

## Consequências

- Feedback rápido no editor e no commit; profundidade no CI.
- Custo: duas ferramentas para manter — mitigado por configs no repo e pré-commit único.
