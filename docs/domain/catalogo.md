# Catálogo de regras — RN/RM

Fonte normativa completa: [`docs/PLANO-REVAMP.md`](../PLANO-REVAMP.md) (§4.3 e §4.4).
Aqui fica a rastreabilidade entre regra, implementação e teste.

## Regras de negócio (RN)

| Regra | Implementação | Teste |
|---|---|---|
| RN-01 papéis e ≥1 owner | `shared/errors.py`, `identity/domain/value_objects.py` (`role_at_least`) | `tests/unit/test_identity_domain.py` |
| RN-02 escopo por workspace (404 p/ não-membro) | `identity/interface/deps.py`, repositórios com `workspace_id` | `tests/integration/test_tenant_isolation.py` |
| RN-03 convite único/expira em 7 dias | `identity/domain/entities.py` (`Invite`) | `test_identity_domain.py` |
| RN-04 senha ≥10, Argon2id | `platform/security.py`, `identity/application/use_cases.py` | `test_auth_flow.py` |
| RN-05 chave de projeto única | `work/interface/router.py`, `SqlProjectRepository.key_exists` | `test_work_flow.py` |
| RN-06 colunas cobrem categorias | `work/domain/entities.py` (`Board.with_default_columns`) | `test_work_domain.py` |
| RN-07 subtasks/pontos | `work/domain/policies.py` | `test_work_domain.py` |
| RN-08…13 hierarquia, pontos, transições, WIP | `work/domain/entities.py` (`WorkItem`), `policies.py` | `test_work_domain.py`, `test_work_flow.py` |
| RN-14…18 sprints (duração, única ativa, goal, imutável, carryover) | `work/domain/entities.py` (`Sprint`), `application/use_cases.py` | `test_work_domain.py`, `test_work_flow.py` |
| RN-19…22 integrações (ownership, idempotência, cripto, desconexão) | `integrations/*` | `test_jira_flow.py`, `test_trello_flow.py`, `test_integrations_unit.py`, `test_trello_unit.py` |
| RN-23…25 auditoria (evento por mutação, soft delete, append-only) | `platform/events.py`, repositórios | `tests/integration/test_events.py` |

## Regras de métricas (RM)

| Regra | Implementação | Teste |
|---|---|---|
| RM-01 dias úteis + timezone do workspace | `metrics/domain/calculators.py` (`working_days_between`, `end_of_day`) | `test_metrics_calculators.py` (golden + hipótese de fronteira) |
| RM-02…06 burndown, escopo por evento, ideal, freeze | `build_burndown` | `test_metrics_calculators.py`, `test_metrics_api.py` |
| RM-07 burnup | dados de `completed`/`scope` na série | (UI consome a mesma série) |
| RM-08…09 velocity/throughput | `build_velocity` | `test_metrics_calculators.py`, `test_metrics_api.py` |
| RM-10 cycle/lead time p50/85/95 | `build_flow_times`, `percentile` | `test_metrics_calculators.py` |
| RM-11 CFD | `build_cfd` | `test_metrics_calculators.py` |
| RM-12 carryover não recontabiliza | `CompleteSprint` + `build_velocity` | `test_work_flow.py` |
| RM-13 sem estimativa à parte | `BurndownTotals.unestimated_items` | `test_metrics_calculators.py` |
| RM-14 snapshots idempotentes | (cron — Fase 5) | pendente |
| RM-15 anti-padrões barrados | design do event log + testes de invariantes | `test_metrics_calculators.py` (`hypothesis`) |

## Convenções transversais

- Erros HTTP: RFC 9457 (`application/problem+json`) com `code` estável — `platform/errors.py`.
- Eventos: `aggregate_type`, payload serializado, `occurred_at` UTC — `platform/orm.py`.
- Fronteiras entre contextos: `[tool.importlinter]` no `pyproject.toml` (4 contratos).
- i18n: chaves estáveis no frontend; API nunca devolve texto traduzido.
