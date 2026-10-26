"""E3 - historico e auditoria sao append-only, garantidos por trigger no PostgreSQL."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.domain.estados import Estado, Perfil, TipoAcao
from app.models import Auditoria, HistoricoLiberacao
from tests.integration import factories as f

pytestmark = pytest.mark.integration


@pytest.fixture
def cenario(session):
    usuario = f.novo_usuario(session)
    aluno = f.novo_aluno(session)
    lib = f.nova_liberacao(session, aluno, usuario)
    hist = f.novo_historico(session, lib, usuario)
    session.commit()
    return usuario, aluno, lib, hist


def test_update_no_historico_e_bloqueado(session, cenario):
    _, _, _, hist = cenario
    with pytest.raises(IntegrityError, match="append-only"):
        session.execute(
            text(f"UPDATE historico_liberacoes SET motivo = 'adulterado' WHERE id = {hist.id}")
        )


def test_delete_no_historico_e_bloqueado(session, cenario):
    _, _, _, hist = cenario
    with pytest.raises(IntegrityError, match="append-only"):
        session.execute(text(f"DELETE FROM historico_liberacoes WHERE id = {hist.id}"))


def test_truncate_no_historico_e_bloqueado(session, cenario):
    with pytest.raises(IntegrityError, match="append-only"):
        session.execute(text("TRUNCATE historico_liberacoes"))


def test_auditoria_tambem_e_append_only(session, cenario):
    usuario = cenario[0]
    ev = Auditoria(
        usuario_id=usuario.id,
        perfil=Perfil.ADMIN,
        tipo_evento="ALUNO_CRIADO",
        entidade="alunos",
        entidade_id=1,
    )
    session.add(ev)
    session.commit()
    with pytest.raises(IntegrityError, match="append-only"):
        session.execute(text(f"UPDATE auditoria SET tipo_evento = 'X' WHERE id = {ev.id}"))
    session.rollback()
    with pytest.raises(IntegrityError, match="append-only"):
        session.execute(text(f"DELETE FROM auditoria WHERE id = {ev.id}"))


def test_liberacao_com_historico_nao_pode_ser_excluida(session, cenario):
    _, _, lib, _ = cenario
    with pytest.raises(IntegrityError):
        session.execute(text(f"DELETE FROM liberacoes WHERE id = {lib.id}"))


def test_historico_sobrevive_a_desativacao_do_aluno_e_do_usuario(session, cenario):
    usuario, aluno, _, _ = cenario
    aluno.ativo = False
    usuario.ativo = False
    session.commit()
    assert session.scalar(select(func.count()).select_from(HistoricoLiberacao)) == 1


def test_historico_nao_aceita_estado_anterior_igual_ao_novo(session, cenario):
    usuario, _, lib, _ = cenario
    with pytest.raises(IntegrityError):
        f.novo_historico(
            session,
            lib,
            usuario,
            estado_anterior=Estado.LIBERADO,
            novo_estado=Estado.LIBERADO,
            tipo_acao=TipoAcao.LIBERACAO,
        )


def test_correcao_admin_exige_motivo(session, cenario):
    usuario, _, lib, _ = cenario
    with pytest.raises(IntegrityError):
        f.novo_historico(
            session,
            lib,
            usuario,
            perfil=Perfil.ADMIN,
            estado_anterior=Estado.LIBERADO,
            novo_estado=Estado.CANCELADO,
            tipo_acao=TipoAcao.CORRECAO_ADMIN,
            motivo="   ",
        )


def test_correcao_admin_com_motivo_e_aceita(session, cenario):
    usuario, _, lib, _ = cenario
    h = f.novo_historico(
        session,
        lib,
        usuario,
        perfil=Perfil.ADMIN,
        estado_anterior=Estado.LIBERADO,
        novo_estado=Estado.CANCELADO,
        tipo_acao=TipoAcao.CORRECAO_ADMIN,
        motivo="Pedido da coordenacao",
    )
    assert h.id is not None


def test_criacao_inicial_tem_estado_anterior_nulo(session, cenario):
    assert cenario[3].estado_anterior is None


def test_horario_do_evento_e_gerado_pelo_servidor(session, cenario):
    hist = cenario[3]
    session.refresh(hist)
    agora = session.scalar(text("SELECT now()"))
    assert hist.ocorrido_em.tzinfo is not None
    assert abs(agora - hist.ocorrido_em) < timedelta(minutes=1)
    assert hist.ocorrido_em <= datetime.now(UTC) + timedelta(minutes=1)


@pytest.mark.parametrize(
    "coluna, valor",
    [("perfil", "VISITANTE"), ("novo_estado", "NAO_LIBERADO"), ("tipo_acao", "DESFAZER")],
)
def test_valores_invalidos_no_historico_sao_rejeitados(session, cenario, coluna, valor):
    usuario, aluno, lib, _ = cenario
    base = {
        "liberacao_id": lib.id,
        "aluno_id": aluno.id,
        "usuario_id": usuario.id,
        "perfil": "RESPONSAVEL",
        "estado_anterior": None,
        "novo_estado": "LIBERADO",
        "tipo_acao": "LIBERACAO",
    }
    base[coluna] = valor
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO historico_liberacoes "
                "(liberacao_id, aluno_id, usuario_id, perfil, estado_anterior, "
                "novo_estado, tipo_acao) VALUES "
                "(:liberacao_id, :aluno_id, :usuario_id, :perfil, :estado_anterior, "
                ":novo_estado, :tipo_acao)"
            ),
            base,
        )