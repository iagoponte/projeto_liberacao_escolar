
"""Testes da correção administrativa auditável."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.api.conftest import login

from app.domain.estados import Estado, Perfil, TipoAcao
from app.models import (
    HistoricoLiberacao,
    Liberacao,
    Usuario,
)
from tests.api.test_matriculas import (
    autenticar_admin,
    criar_aluno,
    criar_ano,
    criar_turma,
    payload_matricula,
)


def test_admin_corrige_liberacao_com_justificativa_e_auditoria(
    client_db,
    criar_usuario,
    db,
):
    # ARRANGE — administração autenticada
    headers = autenticar_admin(
        client_db,
        criar_usuario,
    )

    ano_id = criar_ano(
        client_db,
        headers,
        ano=2026,
    )

    turma_id = criar_turma(
        client_db,
        headers,
        ano_id,
        identificacao="1 Ano A",
    )

    aluno_id = criar_aluno(
        client_db,
        headers,
        matricula="CORRECAO-001",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers,
    )

    assert matricula.status_code == 201

    # Identificar o administrador real, sem ID fixo.
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
            estado=Estado.LIBERADO,
            atualizado_por_usuario_id=admin_id,
        )

        sessao.add(liberacao)
        sessao.commit()

        liberacao_id = liberacao.id

    # ACT — correção administrativa
    motivo = "Solicitacao registrada pela secretaria."

    resposta = client_db.patch(
        f"/admin/alunos/{aluno_id}/liberacao",
        json={
            "estado": "CANCELADO",
            "motivo": motivo,
        },
        headers=headers,
    )

    # ASSERT — contrato HTTP
    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["aluno_id"] == aluno_id
    assert dados["data"] == "2026-10-20"
    assert dados["estado"] == "CANCELADO"

    # ASSERT — estado atual persistido
    with Session(db) as sessao:
        liberacao_atual = sessao.get(
            Liberacao,
            liberacao_id,
        )

        assert liberacao_atual is not None
        assert liberacao_atual.estado == Estado.CANCELADO
        assert (
            liberacao_atual.atualizado_por_usuario_id
            == admin_id
        )

        # ASSERT — histórico obrigatório
        historicos = sessao.scalars(
            select(HistoricoLiberacao).where(
                HistoricoLiberacao.liberacao_id
                == liberacao_id
            )
        ).all()

        assert len(historicos) == 1

        historico = historicos[0]

        assert historico.usuario_id == admin_id
        assert historico.perfil == Perfil.ADMIN
        assert historico.tipo_acao == TipoAcao.CORRECAO_ADMIN
        assert historico.estado_anterior == Estado.LIBERADO
        assert historico.novo_estado == Estado.CANCELADO
        assert historico.motivo == motivo


def test_admin_nao_corrige_com_justificativa_vazia(
    client_db,
    criar_usuario,
):
    headers = autenticar_admin(client_db, criar_usuario)

    aluno_id = criar_aluno(
        client_db,
        headers,
        matricula="CORRECAO-SEM-MOTIVO",
    )

    resposta = client_db.patch(
        f"/admin/alunos/{aluno_id}/liberacao",
        json={
            "estado": "LIBERADO",
            "motivo": "   ",
        },
        headers=headers,
    )

    assert resposta.status_code == 422


def test_admin_nao_corrige_para_o_mesmo_estado(
    client_db,
    criar_usuario,
    db,
):
    headers = autenticar_admin(client_db, criar_usuario)

    ano_id = criar_ano(
        client_db,
        headers,
        ano=2026,
    )

    turma_id = criar_turma(
        client_db,
        headers,
        ano_id,
        identificacao="1 Ano A",
    )

    aluno_id = criar_aluno(
        client_db,
        headers,
        matricula="CORRECAO-REDUNDANTE",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers,
    )
    assert matricula.status_code == 201

    with Session(db) as sessao:
        admin_id = sessao.scalar(
            select(Usuario.id).where(
                Usuario.perfil == Perfil.ADMIN
            )
        )
        assert admin_id is not None

        sessao.add(
            Liberacao(
                aluno_id=aluno_id,
                data=date(2026, 10, 20),
                estado=Estado.LIBERADO,
                atualizado_por_usuario_id=admin_id,
            )
        )
        sessao.commit()

    resposta = client_db.patch(
        f"/admin/alunos/{aluno_id}/liberacao",
        json={
            "estado": "LIBERADO",
            "motivo": "Tentativa de correcao redundante.",
        },
        headers=headers,
    )

    assert resposta.status_code == 409

    # Nenhuma correção redundante deve gerar auditoria.
    with Session(db) as sessao:
        historicos = sessao.scalars(
            select(HistoricoLiberacao).where(
                HistoricoLiberacao.aluno_id == aluno_id
            )
        ).all()

        assert historicos == []


def test_admin_nao_corrige_aluno_sem_matricula_vigente(
    client_db,
    criar_usuario,
):
    headers = autenticar_admin(client_db, criar_usuario)

    aluno_id = criar_aluno(
        client_db,
        headers,
        matricula="CORRECAO-SEM-MATRICULA",
    )

    resposta = client_db.patch(
        f"/admin/alunos/{aluno_id}/liberacao",
        json={
            "estado": "LIBERADO",
            "motivo": "Solicitacao registrada pela secretaria.",
        },
        headers=headers,
    )

    assert resposta.status_code == 409


def test_responsavel_nao_pode_corrigir_liberacao_admin(
    client_db,
    criar_usuario,
    criar_responsavel,
):
    # Criar e autenticar um responsável.
    criar_responsavel()

    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    headers = {
        "X-CSRF-Token": autenticacao.json()["csrf_token"]
    }

    resposta = client_db.patch(
        "/admin/alunos/1/liberacao",
        json={
            "estado": "CANCELADO",
            "motivo": "Tentativa nao autorizada.",
        },
        headers=headers,
    )

    assert resposta.status_code == 403
