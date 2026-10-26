
"""Testes da consulta administrativa do histórico de liberações."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.estados import Estado, Perfil, TipoAcao
from app.models import (
    HistoricoLiberacao,
    Liberacao,
    Usuario,
)
from tests.api.test_matriculas import (
    autenticar_admin,
    criar_aluno,
)


def test_admin_consulta_historico_de_liberacoes(
    client_db,
    criar_usuario,
    db,
):
    # ARRANGE — administrador autenticado
    headers = autenticar_admin(
        client_db,
        criar_usuario,
    )

    aluno_id = criar_aluno(
        client_db,
        headers,
        matricula="HIST-ADMIN-001",
    )

    instante_inicial = datetime(
        2026, 10, 20, 10, 0,
        tzinfo=timezone.utc,
    )

    with Session(db) as sessao:
        admin_id = sessao.scalar(
            select(Usuario.id).where(
                Usuario.perfil == Perfil.ADMIN
            )
        )
        assert admin_id is not None

        liberacao = Liberacao(
            aluno_id=aluno_id,
            data=date(2026, 10, 20),
            estado=Estado.CANCELADO,
            atualizado_por_usuario_id=admin_id,
        )

        sessao.add(liberacao)
        sessao.flush()

        sessao.add_all([
            HistoricoLiberacao(
                liberacao_id=liberacao.id,
                aluno_id=aluno_id,
                usuario_id=admin_id,
                perfil=Perfil.ADMIN,
                ocorrido_em=instante_inicial,
                estado_anterior=None,
                novo_estado=Estado.LIBERADO,
                tipo_acao=TipoAcao.LIBERACAO,
                motivo=None,
            ),
            HistoricoLiberacao(
                liberacao_id=liberacao.id,
                aluno_id=aluno_id,
                usuario_id=admin_id,
                perfil=Perfil.ADMIN,
                ocorrido_em=instante_inicial + timedelta(minutes=10),
                estado_anterior=Estado.LIBERADO,
                novo_estado=Estado.CANCELADO,
                tipo_acao=TipoAcao.CANCELAMENTO,
                motivo=None,
            ),
        ])

        sessao.commit()

    # ACT — consultar o histórico administrativo
    resposta = client_db.get(
        f"/admin/alunos/{aluno_id}/liberacoes/historico",
        headers=headers,
    )

    # ASSERT — contrato HTTP
    assert resposta.status_code == 200

    historico = resposta.json()

    assert len(historico) == 2

    # Evento mais recente primeiro
    assert historico[0]["tipo_acao"] == "CANCELAMENTO"
    assert historico[0]["estado_anterior"] == "LIBERADO"
    assert historico[0]["novo_estado"] == "CANCELADO"

    assert historico[1]["tipo_acao"] == "LIBERACAO"
    assert historico[1]["estado_anterior"] is None
    assert historico[1]["novo_estado"] == "LIBERADO"

    assert all(
        evento["aluno_id"] == aluno_id
        for evento in historico
    )
