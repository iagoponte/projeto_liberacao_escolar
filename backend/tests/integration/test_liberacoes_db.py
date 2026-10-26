"""E3 - registro de liberacao: um por aluno e data, apenas estados validos."""
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.domain.estados import Estado
from app.models import Liberacao
from tests.integration import factories as f

pytestmark = pytest.mark.integration


def test_liberacao_duplicada_para_mesmo_aluno_e_data_e_rejeitada(session):
    a = f.novo_aluno(session)
    f.nova_liberacao(session, a)
    session.add(Liberacao(aluno_id=a.id, data=f.HOJE, estado=Estado.CANCELADO))
    with pytest.raises(IntegrityError):
        session.flush()


def test_mesmo_aluno_em_outra_data_e_permitido(session):
    a = f.novo_aluno(session)
    f.nova_liberacao(session, a, data=date(2026, 10, 20))
    f.nova_liberacao(session, a, data=date(2026, 10, 21))


def test_mesma_data_para_outro_aluno_e_permitida(session):
    f.nova_liberacao(session, f.novo_aluno(session))
    f.nova_liberacao(session, f.novo_aluno(session))


def test_estado_invalido_e_rejeitado(session):
    a = f.novo_aluno(session)
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO liberacoes (aluno_id, data, estado) "
                f"VALUES ({a.id}, '2026-10-20', 'NAO_LIBERADO')"
            )
        )


def test_liberacao_exige_aluno_existente(session):
    session.add(Liberacao(aluno_id=999999, data=f.HOJE, estado=Estado.LIBERADO))
    with pytest.raises(IntegrityError):
        session.flush()


def test_liberacao_exige_data(session):
    a = f.novo_aluno(session)
    with pytest.raises(IntegrityError):
        session.execute(
            text(f"INSERT INTO liberacoes (aluno_id, estado) VALUES ({a.id}, 'LIBERADO')")
        )