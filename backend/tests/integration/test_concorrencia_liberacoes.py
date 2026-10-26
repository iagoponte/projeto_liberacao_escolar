
"""E5.4-E — Concorrência na criação de liberações."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.estados import Estado, Acao
from app.models import Liberacao
from tests.integration import factories as f
from threading import Event, Lock





pytestmark = pytest.mark.integration

DATA_TESTE = date(2026, 10, 20)


def test_duas_transacoes_nao_criam_liberacoes_duplicadas(db):
    # ARRANGE — aluno já persistido no banco.
    with Session(db) as sessao:
        aluno = f.novo_aluno(sessao)
        sessao.commit()
        aluno_id = aluno.id

    # As duas transações devem concluir a consulta inicial
    # antes de qualquer uma tentar inserir.
    barreira = Barrier(2, timeout=10)

    def tentar_criar():
        with Session(db) as sessao:
            existente = sessao.scalar(
                select(Liberacao).where(
                    Liberacao.aluno_id == aluno_id,
                    Liberacao.data == DATA_TESTE,
                )
            )

            assert existente is None

            # Sincronizar as duas transações.
            barreira.wait()

            liberacao = Liberacao(
                aluno_id=aluno_id,
                data=DATA_TESTE,
                estado=Estado.LIBERADO,
            )

            sessao.add(liberacao)

            try:
                sessao.commit()
                return "criada"

            except IntegrityError:
                sessao.rollback()
                return "conflito"

    # ACT — duas sessões SQLAlchemy independentes.
    with ThreadPoolExecutor(max_workers=2) as executor:
        futuros = [
            executor.submit(tentar_criar)
            for _ in range(2)
        ]

        resultados = [
            futuro.result(timeout=15)
            for futuro in futuros
        ]

    # ASSERT — somente uma transação pode confirmar.
    assert sorted(resultados) == [
        "conflito",
        "criada",
    ]

    # ASSERT — existe um único registro persistido.
    with Session(db) as sessao:
        liberacoes = sessao.scalars(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id,
                Liberacao.data == DATA_TESTE,
            )
        ).all()

        assert len(liberacoes) == 1
        assert liberacoes[0].estado == Estado.LIBERADO
