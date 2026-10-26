"""Login, validacao de sessao e logout."""
import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.seguranca import (
    chave_de_tentativa,
    gastar_tempo_de_verificacao,
    hash_token,
    novo_token_sessao,
    verificar_senha,
)
from app.domain.relogio import Relogio
from app.domain.sessao import avaliar_sessao, calcular_expiracao, deve_renovar_ultimo_acesso
from app.models import Auditoria, Sessao, Usuario
from app.services.eventos_seguranca import registrar_evento


class CredenciaisInvalidas(Exception):
    pass


class LoginBloqueado(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Muitas tentativas de login.")
        self.retry_after = retry_after


@dataclass(frozen=True)
class LoginRealizado:
    token: str
    usuario: Usuario


@dataclass(frozen=True)
class Autenticacao:
    usuario: Usuario
    sessao: Sessao


def _segundos_ate_liberar(mais_antiga: datetime, agora: datetime, janela: timedelta) -> int:
    return max(1, math.ceil((mais_antiga + janela - agora).total_seconds()))


def _verificar_bloqueio(
    db: Session, settings: Settings, agora: datetime, chave: str, ip: str
) -> int | None:
    """Segundos ate poder tentar de novo, ou None se nao ha bloqueio."""
    janela = timedelta(minutes=settings.login_janela_minutos)
    desde = agora - janela

    # Por e-mail: so contam as falhas posteriores ao ultimo login bem-sucedido.
    ultimo_sucesso = (
        select(func.coalesce(func.max(Auditoria.id), 0))
        .where(
            Auditoria.tipo_evento == "LOGIN_SUCESSO",
            Auditoria.detalhes["chave"].as_string() == chave,
        )
        .scalar_subquery()
    )
    falhas_email = db.scalars(
        select(Auditoria.ocorrido_em)
        .where(
            Auditoria.tipo_evento == "LOGIN_FALHA",
            Auditoria.detalhes["chave"].as_string() == chave,
            Auditoria.ocorrido_em > desde,
            Auditoria.id > ultimo_sucesso,
        )
        .order_by(Auditoria.ocorrido_em)
    ).all()

    # Por IP: protege contra quem testa muitos e-mails diferentes.
    falhas_ip = db.scalars(
        select(Auditoria.ocorrido_em)
        .where(
            Auditoria.tipo_evento == "LOGIN_FALHA",
            Auditoria.detalhes["ip"].as_string() == ip,
            Auditoria.ocorrido_em > desde,
        )
        .order_by(Auditoria.ocorrido_em)
    ).all()

    esperas = []
    if len(falhas_email) >= settings.login_max_falhas:
        esperas.append(_segundos_ate_liberar(falhas_email[0], agora, janela))
    if len(falhas_ip) >= settings.login_max_falhas_por_ip:
        esperas.append(_segundos_ate_liberar(falhas_ip[0], agora, janela))
    return max(esperas) if esperas else None


def tentar_login(
    db: Session, settings: Settings, relogio: Relogio, email: str, senha: str, ip: str
) -> LoginRealizado:
    agora = relogio.agora()
    email_normalizado = email.strip().lower()
    chave = chave_de_tentativa(email_normalizado)

    espera = _verificar_bloqueio(db, settings, agora, chave, ip)
    if espera is not None:
        registrar_evento(db, agora, "LOGIN_BLOQUEADO", detalhes={"chave": chave, "ip": ip})
        db.commit()
        raise LoginBloqueado(espera)

    usuario = db.scalar(select(Usuario).where(func.lower(Usuario.email) == email_normalizado))
    motivo = None
    if usuario is None:
        gastar_tempo_de_verificacao(senha)
        motivo = "usuario_inexistente"
    elif not usuario.ativo:
        gastar_tempo_de_verificacao(senha)
        motivo = "usuario_inativo"
    elif not verificar_senha(senha, usuario.senha_hash):
        motivo = "senha_invalida"

    if motivo is not None:
        registrar_evento(
            db,
            agora,
            "LOGIN_FALHA",
            usuario_id=usuario.id if usuario else None,
            perfil=usuario.perfil if usuario else None,
            detalhes={"chave": chave, "ip": ip, "motivo": motivo},
        )
        db.commit()
        raise CredenciaisInvalidas

    token = novo_token_sessao()
    db.add(
        Sessao(
            token_hash=hash_token(token),
            usuario_id=usuario.id,
            criada_em=agora,
            ultimo_acesso_em=agora,
            expira_em=calcular_expiracao(agora, settings.session_absolute_minutes),
        )
    )
    registrar_evento(
        db,
        agora,
        "LOGIN_SUCESSO",
        usuario_id=usuario.id,
        perfil=usuario.perfil,
        entidade_id=usuario.id,
        detalhes={"chave": chave, "ip": ip},
    )
    db.commit()
    return LoginRealizado(token=token, usuario=usuario)


def autenticar_sessao(
    db: Session, settings: Settings, relogio: Relogio, token: str
) -> Autenticacao | None:
    """Devolve usuario e sessao se o token e valido; None em qualquer outro caso."""
    sessao = db.scalar(select(Sessao).where(Sessao.token_hash == hash_token(token)))
    if sessao is None:
        return None
    agora = relogio.agora()
    motivo = avaliar_sessao(
        agora=agora,
        expira_em=sessao.expira_em,
        ultimo_acesso_em=sessao.ultimo_acesso_em,
        revogada_em=sessao.revogada_em,
        inatividade_maxima=timedelta(minutes=settings.session_idle_minutes),
    )
    if motivo is not None:
        return None
    usuario = db.get(Usuario, sessao.usuario_id)
    if usuario is None or not usuario.ativo:
        return None
    if deve_renovar_ultimo_acesso(agora, sessao.ultimo_acesso_em):
        sessao.ultimo_acesso_em = agora
        db.commit()
    return Autenticacao(usuario=usuario, sessao=sessao)


def encerrar_sessao(db: Session, relogio: Relogio, auth: Autenticacao) -> None:
    agora = relogio.agora()
    auth.sessao.revogada_em = agora
    registrar_evento(
        db,
        agora,
        "LOGOUT",
        usuario_id=auth.usuario.id,
        perfil=auth.usuario.perfil,
        entidade_id=auth.usuario.id,
    )
    db.commit()