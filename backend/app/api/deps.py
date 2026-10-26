"""Dependencias compartilhadas da API: banco, relogio, configuracao e autenticacao."""
from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.seguranca import csrf_valido
from app.db.session import get_session
from app.domain.relogio import Relogio, RelogioSistema
from app.models import Sessao, Usuario
from app.services.autenticacao import autenticar_sessao
from app.services.eventos_seguranca import registrar_evento

COOKIE_SESSAO = "sessao"
CABECALHO_CSRF = "X-CSRF-Token"
METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}


def get_db() -> Iterator[Session]:
    yield from get_session()


def get_relogio() -> Relogio:
    return RelogioSistema()


def ip_do_cliente(request: Request) -> str:
    # Atras de proxy reverso, configure o proxy para repassar o IP real (E10).
    return request.client.host if request.client else "desconhecido"


@dataclass(frozen=True)
class Autenticado:
    usuario: Usuario
    sessao: Sessao
    token: str


def autenticado(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    relogio: Relogio = Depends(get_relogio),
) -> Autenticado:
    """Exige sessao valida; em metodos que alteram estado, exige tambem o token CSRF."""
    token = request.cookies.get(COOKIE_SESSAO)
    resultado = autenticar_sessao(db, settings, relogio, token) if token else None
    if resultado is None:
        raise HTTPException(status_code=401, detail="Nao autenticado.")

    if request.method not in METODOS_SEGUROS and not csrf_valido(
        settings.secret_key, token, request.headers.get(CABECALHO_CSRF)
    ):
        registrar_evento(
            db,
            relogio.agora(),
            "CSRF_INVALIDO",
            usuario_id=resultado.usuario.id,
            perfil=resultado.usuario.perfil,
            entidade_id=resultado.usuario.id,
            detalhes={"rota": request.url.path, "metodo": request.method},
        )
        db.commit()
        raise HTTPException(status_code=403, detail="Token CSRF invalido.")

    return Autenticado(usuario=resultado.usuario, sessao=resultado.sessao, token=token)


def exigir_admin(
    usuario: Autenticado = Depends(autenticado),
) -> Autenticado:
    """Permite acesso somente a usuarios administrativos."""
    from app.domain.estados import Perfil

    if usuario.usuario.perfil != Perfil.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Acesso restrito a administracao.",
        )

    return usuario


def exigir_responsavel(
    usuario: Autenticado = Depends(autenticado),
) -> Autenticado:
    """Permite acesso somente a usuarios responsaveis."""
    from app.domain.estados import Perfil

    if usuario.usuario.perfil != Perfil.RESPONSAVEL:
        raise HTTPException(
            status_code=403,
            detail="Acesso restrito a responsaveis.",
        )

    return usuario
