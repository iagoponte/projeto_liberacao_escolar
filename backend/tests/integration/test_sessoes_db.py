"""E4 - tabela de sessoes: somente hash do token, prazos coerentes, historico preservado."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.seguranca import hash_token
from app.models import Sessao
from tests.integration import factories as f

pytestmark = pytest.mark.integration

T0 = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)


def nova_sessao(session, usuario, token="token-1", **kw):
    campos = dict(
        token_hash=hash_token(token),
        usuario_id=usuario.id,
        criada_em=T0,
        ultimo_acesso_em=T0,
        expira_em=T0 + timedelta(hours=8),
    )
    campos.update(kw)
    s = Sessao(**campos)
    session.add(s)
    session.flush()
    return s


def test_token_hash_e_unico(session):
    u = f.novo_usuario(session)
    nova_sessao(session, u, "token-1")
    with pytest.raises(IntegrityError):
        nova_sessao(session, u, "token-1")


def test_varias_sessoes_do_mesmo_usuario_sao_permitidas(session):
    u = f.novo_usuario(session)
    nova_sessao(session, u, "token-1")
    nova_sessao(session, u, "token-2")
    assert session.scalar(select(func.count()).select_from(Sessao)) == 2


def test_sessao_exige_usuario_existente(session):
    with pytest.raises(IntegrityError):
        session.add(
            Sessao(
                token_hash=hash_token("x"),
                usuario_id=999999,
                criada_em=T0,
                ultimo_acesso_em=T0,
                expira_em=T0 + timedelta(hours=8),
            )
        )
        session.flush()


def test_expiracao_deve_ser_posterior_a_criacao(session):
    u = f.novo_usuario(session)
    with pytest.raises(IntegrityError):
        nova_sessao(session, u, expira_em=T0)


def test_token_hash_deve_ter_64_caracteres(session):
    u = f.novo_usuario(session)
    with pytest.raises(IntegrityError):
        nova_sessao(session, u, token_hash="curto")


def test_usuario_com_sessao_nao_pode_ser_excluido(session):
    u = f.novo_usuario(session)
    nova_sessao(session, u)
    with pytest.raises(IntegrityError):
        session.execute(text(f"DELETE FROM usuarios WHERE id = {u.id}"))


def test_revogar_preserva_o_registro(session):
    u = f.novo_usuario(session)
    s = nova_sessao(session, u)
    s.revogada_em = T0 + timedelta(minutes=5)
    session.flush()
    assert session.scalar(select(func.count()).select_from(Sessao)) == 1