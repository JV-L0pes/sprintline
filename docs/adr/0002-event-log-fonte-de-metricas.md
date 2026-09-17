# ADR 0002 — Event log append-only como fonte de verdade das métricas

- Status: aceito
- Data: 2026-09-16
- Contexto: o burndown do projeto original era derivado de totais atuais, o que impedia reconstruir histórico, detectar mudanças de escopo e calcular velocity/CFD/cycle time com confiança.

## Decisão

Toda mutação de agregado appenda um evento imutável em `domain_events` (`actor_id`, `occurred_at` UTC, `source`, payload). Métricas são projeções puras calculadas a partir do event log (`metrics/domain/calculators.py`), com snapshots diários idempotentes. O append acontece na camada de repositório via `EventRecorder` em `session.info`, garantindo a invariante "toda escrita gera evento" sem plumbing nos casos de uso.

## Consequências

- Burndown/burnup/CFD reconstruíveis a qualquer momento (replay determinístico).
- Mudança de escopo aparece como degrau visível; nada é reescrito retroativamente.
- Testes de propriedade garantem invariantes (restante ≥ 0, ideal nos extremos, concluído monotônico).
- Custo: tabela cresce monotonicamente; retenção definida pela vida do workspace (cascata no purge).
