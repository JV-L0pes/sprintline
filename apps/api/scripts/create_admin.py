"""Bootstrap de instancia privada: cria o primeiro usuario owner.

Com registro invite_only nao ha como criar a primeira conta pela UI; este
script cria o usuario (ignorando o modo de registro) e, opcionalmente, um
workspace com ele como owner.

Uso:
    uv run python scripts/create_admin.py --email voce@exemplo.com --name "Seu Nome" \
        --workspace "Meu Workspace"

Sem --password, uma senha temporaria e gerada e impressa (troque no primeiro
acesso pela tela de configuracoes). Idempotente: se o email ja existe, nao
recria o usuario.
"""

from __future__ import annotations

import argparse
import asyncio
import secrets

from cadencia.identity.application.use_cases import CreateWorkspace, RegisterUser
from cadencia.identity.infrastructure import orm as identity_orm  # noqa: F401
from cadencia.identity.infrastructure.repositories import (
    SqlMembershipRepository,
    SqlOrganizationRepository,
    SqlUserRepository,
    SqlWorkspaceRepository,
)
from cadencia.identity.infrastructure.security import Argon2PasswordHasher
from cadencia.integrations.infrastructure import orm as integrations_orm  # noqa: F401
from cadencia.platform import orm as platform_orm  # noqa: F401
from cadencia.platform.config import get_settings
from cadencia.platform.db import Base, build_engine, build_session_factory
from cadencia.shared.clock import SystemClock
from cadencia.work.infrastructure import orm as work_orm  # noqa: F401


async def main() -> None:
    parser = argparse.ArgumentParser(description="Cria o primeiro owner da instancia.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--password", default=None)
    parser.add_argument("--workspace", default=None, help="Nome do workspace inicial (opcional)")
    args = parser.parse_args()

    password = args.password or secrets.token_urlsafe(12)
    settings = get_settings()
    engine = build_engine(settings)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = build_session_factory(engine)
    clock = SystemClock()

    async with factory() as session:
        users = SqlUserRepository(session)
        existing = await users.find_by_email(args.email)
        if existing is not None:
            print(f"Usuario {args.email} ja existe (id {existing.id}). Nada a fazer.")
            await engine.dispose()
            return

        user = await RegisterUser(users, Argon2PasswordHasher(), clock).execute(
            email=args.email, name=args.name, password=password, locale="pt-BR"
        )
        workspace_line = "  workspace: (nenhum)"
        if args.workspace:
            view = await CreateWorkspace(
                SqlOrganizationRepository(session),
                SqlWorkspaceRepository(session),
                SqlMembershipRepository(session),
                clock,
            ).execute(user=user, name=args.workspace, timezone="America/Sao_Paulo")
            workspace_line = f"  workspace: {view.name} (slug {view.slug})"
        await session.commit()

    await engine.dispose()
    print("Owner criado com sucesso.")
    print(f"  email:   {args.email}")
    print(f"  senha:   {password}")
    print(workspace_line)
    print("Troque a senha no primeiro acesso (Configuracoes > Alterar minha senha).")


if __name__ == "__main__":
    asyncio.run(main())
