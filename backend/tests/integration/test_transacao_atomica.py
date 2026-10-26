"""E3 - alteracao de estado e historico na MESMA transacao: tudo ou nada."""
import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.estados import Estado, Perfil, TipoAcao
from app.models import HistoricoLiberacao, Liberacao
from tests.integration import factories as f

pytestmark = pytest.mark.integration


def contar(s, modelo):
    return s.scalar(select(func.count()).select_from(modelo))


def test_commit_grava_liberacao_e_historico_juntos(db):
    with Session(db) as s:
        u, a = f.novo_usuario(s), f.novo_aluno(s)
        lib = f.nova_liberacao(s, a, u)
        f.novo_historico(s, lib, u)
        s.commit()
    with Session(db) as s:
        assert contar(s, Liberacao) == 1
        assert contar(s, HistoricoLiberacao) == 1


def test_falha_no_historico_reverte_a_criacao_da_liberacao(db):
    with Session(db) as s:
        u, a = f.novo_usuario(s), f.novo_aluno(s)
        s.commit()
        aluno_id, usuario_id = a.id, u.id

    with Session(db) as s:
        lib = Liberacao(aluno_id=aluno_id, data=f.HOJE, estado=Estado.LIBERADO)
        s.add(lib)
        s.flush()
        s.add(
            HistoricoLiberacao(
                liberacao_id=lib.id,
                aluno_id=aluno_id,
                usuario_id=usuario_id,
                perfil=Perfil.RESPONSAVEL,
                estado_anterior=Estado.LIBERADO,
                novo_estado=Estado.LIBERADO,  # viola o CHECK: nao ha mudanca real
                tipo_acao=TipoAcao.LIBERACAO,
            )
        )
        with pytest.raises(IntegrityError):
            s.commit()

    with Session(db) as s:
        assert contar(s, Liberacao) == 0
        assert contar(s, HistoricoLiberacao) == 0


def test_falha_no_historico_reverte_a_mudanca_de_estado(db):
    with Session(db) as s:
        u, a = f.novo_usuario(s), f.novo_aluno(s)
        lib = f.nova_liberacao(s, a, u, estado=Estado.LIBERADO)
        f.novo_historico(s, lib, u)
        s.commit()
        lib_id, aluno_id, usuario_id = lib.id, a.id, u.id

    with Session(db) as s:
        lib = s.get(Liberacao, lib_id)
        lib.estado = Estado.CANCELADO
        s.flush()
        s.add(
            HistoricoLiberacao(
                liberacao_id=lib_id,
                aluno_id=aluno_id,
                usuario_id=usuario_id,
                perfil=Perfil.RESPONSAVEL,
                estado_anterior=Estado.CANCELADO,
                novo_estado=Estado.CANCELADO,  # invalido
                tipo_acao=TipoAcao.CANCELAMENTO,
            )
        )
        with pytest.raises(IntegrityError):
            s.commit()

    with Session(db) as s:
        assert s.get(Liberacao, lib_id).estado == Estado.LIBERADO
        assert contar(s, HistoricoLiberacao) == 1