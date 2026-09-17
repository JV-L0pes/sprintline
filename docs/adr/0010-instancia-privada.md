# ADR 0010 — Instância privada: invite-only, rate limit e sem demo pública

- Status: aceito
- Data: 2026-09-17
- Contexto: o produto é de uso pessoal/privado (com valor de portfólio), mas o MVP nasceu com
  registro aberto e uma conta de demonstração pública com credenciais conhecidas. Isso permitia
  que qualquer visitante criasse contas e alterasse o workspace demo.

## Decisão

1. **Registro por convite**: `CADENCIA_REGISTRATION_MODE` (`invite_only` por padrão; `open`/`closed`
   como alternativas). O cadastro aceita `invite_token` e valida convite + email antes de criar a
   conta; a UI esconde "Criar conta" fora do modo aberto e a página `/invite/:token` registra inline.
2. **Bootstrap do primeiro owner** via `scripts/create_admin.py` (resolve o ovo-e-galinha de
   instância fechada) — roda direto no banco, ignorando o gate de registro.
3. **Rate limit do auth persistido** (`rate_limit_hits`): login 10/15min por IP+email, registro 5/h,
   refresh 120/h; resposta 429 com `Retry-After`. O contador commita fora da transação da request
   para sobreviver ao rollback de um 401.
4. **Sem demo pública**: conta/workspace demo removidos de produção (`purge_demo.py`) e o seed de
   demonstração passou a recusar execução em produção sem `--force`; permanece apenas para dev/e2e/CI.
5. **Gestão de membros** (papel, remoção, reset de senha) e **troca da própria senha** (revoga todas
   as sessões) entram como o mínimo administrativo para operar um workspace privado.

## Consequências

- Só entra quem for convidado; nenhum dado exposto por credencial padrão.
- Convites seguem o fluxo link → cadastro → aceite idempotente (mesmo usuário pode reabrir o link).
- Operação exige um passo manual de bootstrap por instância (documentado no runbook).
- Custo: sem demonstração pública, o portfólio passa a depender de screenshots/case study em vez de
  um link navegável com login aberto.
