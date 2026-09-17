# ADR 0006 — JWT curto em memória + refresh opaco em cookie com rotação

- Status: aceito
- Data: 2026-09-16
- Contexto: app multi-workspace precisa de sessões seguras sem depender de provedor externo; tokens nunca devem ficar acessíveis a XSS.

## Decisão

Access token JWT (15 min) mantido apenas em memória no frontend; refresh token opaco (30 dias) em cookie `HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth`, **rotacionado a cada uso** com detecção de reuso (família revogada). Argon2id para senhas. A revogação por reuso é commitada explicitamente antes de responder 401 (o rollback do Unit of Work padrão não pode desfazer um efeito de segurança).

## Consequências

- XSS não exporta refresh token; roubo do refresh é detectado na próxima rotação.
- Custo: coordenação frontend (boot faz refresh silencioso para rehidratar a sessão).
