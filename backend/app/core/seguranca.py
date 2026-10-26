"""Primitivas de seguranca: hash de senha, token de sessao e CSRF."""
import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()  # Argon2id com os parametros padrao recomendados
_hash_falso: str | None = None


def hash_senha(senha: str) -> str:
    return _hasher.hash(senha)


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    """Nunca levanta excecao: hash invalido ou senha errada resultam em False."""
    try:
        return _hasher.verify(hash_armazenado, senha)
    except (VerificationError, InvalidHashError):
        return False


def gastar_tempo_de_verificacao(senha: str) -> None:
    """Equaliza o tempo de resposta quando o usuario nao existe (evita enumeracao)."""
    global _hash_falso
    if _hash_falso is None:
        _hash_falso = _hasher.hash("hash-falso-para-equalizar-tempo")
    verificar_senha(senha, _hash_falso)


def novo_token_sessao() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Somente o hash do token fica no banco: um vazamento nao permite sequestrar sessoes."""
    return hashlib.sha256(token.encode()).hexdigest()


def token_csrf(segredo: str, token_sessao: str) -> str:
    return hmac.new(segredo.encode(), f"csrf:{token_sessao}".encode(), hashlib.sha256).hexdigest()


def csrf_valido(segredo: str, token_sessao: str, apresentado: str | None) -> bool:
    if not apresentado:
        return False
    return hmac.compare_digest(token_csrf(segredo, token_sessao), apresentado)


def chave_de_tentativa(email: str) -> str:
    """Identifica as tentativas de login de um e-mail sem gravar o e-mail em claro."""
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()