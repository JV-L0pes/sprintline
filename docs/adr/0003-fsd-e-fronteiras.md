# ADR 0003 — Feature-Sliced Design no frontend

- Status: aceito
- Data: 2026-09-16
- Contexto: o frontend original era uma página com funções globais e DOM manipulation; o produto agora tem board, backlog, métricas, membros e integrações.

## Decisão

Organizar `apps/web` em camadas FSD (`app → pages → widgets → features → entities → shared`), com slices por domínio e `index.ts` públicos. Regras de import são convenção revisada em PR; ESLint/TypeScript garantem tipos e hooks, Biome a formatação.

## Consequências

- Features isoladas (criar item, mover, iniciar sprint) reutilizadas por board e backlog.
- Modelos puros em `entities/*/model.ts` são o alvo dos testes unitários.
- Sem `dependency-cruiser` por enquanto — projeto pequeno; a regra é documentada e verificada em review (candidato a automatizar quando o time crescer).
