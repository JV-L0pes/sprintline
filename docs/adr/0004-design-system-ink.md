# ADR 0004 — Design system "Ink" (Tailwind v4 + shadcn)

- Status: aceito
- Data: 2026-09-16
- Contexto: o portfólio do autor ("Ink") é a referência estética: editorial, monocrômico, tipografia como interface, ouro racionado a status.

## Decisão

Portar os tokens do portfólio (paper/ink/ash/rule/gold, easing `--ease`/`--soft`, Archivo `wdth` + Martian Mono) para Tailwind v4 CSS-first (`@theme inline`) e construir os primitivos (button, input, dialog, badge…) sobre eles, com raio 0 e sem sombras. Gráficos usam os mesmos tokens via CSS variables em SVG.

## Consequências

- Identidade forte e coerente com o portfólio; acessível (foco 2px ink, reduced-motion global).
- Sem libs de UI pesadas; componentes próprios pequenos e testáveis.
- Custo: componentes que o shadcn traria prontos são mantidos aqui (superfície pequena e controlada).
