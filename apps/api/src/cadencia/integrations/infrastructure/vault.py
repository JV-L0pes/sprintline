"""Criptografia de tokens em repouso (AES via Fernet) — RN-21."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from cadencia.shared.errors import ValidationError


class TokenVault:
    def __init__(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    def encrypt(self, raw: str) -> str:
        return self._fernet.encrypt(raw.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise ValidationError(
                "Falha ao decifrar token da integracao; verifique INTEGRATION_SECRET_KEY",
                code="TOKEN_DECRYPT_FAILED",
            ) from exc
