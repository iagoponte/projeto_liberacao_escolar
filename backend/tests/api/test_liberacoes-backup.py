
"""E5.4-A — Testes de liberação escolar pelo responsável."""

from datetime import date, time

import pytest
from sqlalchemy import select, event
from sqlalchemy.orm import Session

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from threading import Event, Lock

from app.domain.estados import Estado, Perfil, TipoAcao, Acao
from app.models import HistoricoLiberacao, Liberacao, Aluno, ResponsavelAluno
from tests.api.conftest import login
from tests.api.test_matriculas import (
    autenticar_admin,
    criar_aluno,
    criar_ano,
    criar_turma,
    payload_matricula,
)
from tests.api.test_vinculos import criar_vinculo
from app.services import liberacoes as servico_liberacoes
from app.services.liberacoes import executar_liberacao_responsavel
from app.models import GradeHorario, AulaRecorrente




pytestmark = pytest.mark.integration


def test_responsavel_libera_aluno_vinculado_na_data_atual(
    client_db,
    criar_usuario,
    criar_responsavel,
    db,
):
    # ARRANGE — responsável com cadastro ativo
    responsavel_id = criar_responsavel()

    # Administração autenticada
    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    # Ano letivo e turma da manhã em 2026
    ano_id = criar_ano(
        client_db,
        headers_admin,
        ano=2026,
    )

    turma_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano A",
    )
    
    with Session(db) as session:
        grade = GradeHorario(
            turma_id=turma_id,
            vigente_desde=date(2026, 2, 1),
            vigente_ate=None,
            horarios=["08:00", "08:50"],
            hora_termino=time(9, 40),
        )

        session.add(grade)
        session.flush()

        # 20/10/2026 é terça-feira: weekday() == 1.
        session.add(
            AulaRecorrente(
                grade_id=grade.id,
                dia_semana=1,
                hora_inicio=time(8, 0),
                descricao="Matemática",
                tipo="AULA",
            )
        )

        session.commit()
    
    assert resposta.status_code == 200, resposta.json()

    dados = resposta.json()

    assert dados["estado"] == "LIBERADO"
    assert dados["horario_inicio_liberacao"] == "08:00:00"

    # Aluno ativo
    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="LIB-001",
    )

    # Matrícula vigente em 20/10/2026
    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers_admin,
    )

    assert matricula.status_code == 201

    # Vínculo vigente com o responsável
    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )

    assert vinculo.status_code == 201

    # Autenticar como responsável
    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )

    assert autenticacao.status_code == 200

    usuario_id = autenticacao.json()["usuario"]["id"]

    headers_responsavel = {
        "X-CSRF-Token": autenticacao.json()["csrf_token"]
    }

    # ACT — solicitar liberação
    resposta = client_db.post(
        f"/responsavel/alunos/{aluno_id}/liberacao",
        json={
            "acao": "LIBERAR",
            "horario_inicio_liberacao": "08:00",
        },
        headers=headers_responsavel,
    )

    # ASSERT — contrato HTTP
    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["aluno_id"] == aluno_id
    assert dados["data"] == "2026-10-20"
    assert dados["estado"] == "LIBERADO"

    # ASSERT — persistência e auditoria
    with Session(db) as sessao:
        liberacoes = sessao.scalars(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id,
                Liberacao.data == date(2026, 10, 20),
            )
        ).all()

        assert len(liberacoes) == 1

        liberacao = liberacoes[0]

        assert liberacao.estado == Estado.LIBERADO
        assert liberacao.atualizado_por_usuario_id == usuario_id

        historicos = sessao.scalars(
            select(HistoricoLiberacao).where(
                HistoricoLiberacao.liberacao_id == liberacao.id
            )
        ).all()

        assert len(historicos) == 1

        evento = historicos[0]

        assert evento.aluno_id == aluno_id
        assert evento.usuario_id == usuario_id
        assert evento.perfil == Perfil.RESPONSAVEL
        assert evento.estado_anterior is None
        assert evento.novo_estado == Estado.LIBERADO
        assert evento.tipo_acao == TipoAcao.LIBERACAO


def test_liberacao_repetida_nao_gera_novo_historico(
    client_db,
    criar_usuario,
    criar_responsavel,
    db,
):
    # ARRANGE — responsável, aluno e matrícula vigente
    responsavel_id = criar_responsavel()

    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    ano_id = criar_ano(
        client_db,
        headers_admin,
        ano=2026,
    )

    turma_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano A",
    )

    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="LIB-REDUND-001",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers_admin,
    )
    assert matricula.status_code == 201

    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert vinculo.status_code == 201

    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    headers_responsavel = {
        "X-CSRF-Token": autenticacao.json()["csrf_token"]
    }

    url = f"/responsavel/alunos/{aluno_id}/liberacao"

    # ACT — primeira liberação
    primeira = client_db.post(
        url,
        json={"acao": "LIBERAR"},
        headers=headers_responsavel,
    )

    # ACT — solicitação redundante
    segunda = client_db.post(
        url,
        json={"acao": "LIBERAR"},
        headers=headers_responsavel,
    )

    # ASSERT — ambas são aceitas
    assert primeira.status_code == 200
    assert segunda.status_code == 200

    assert primeira.json()["estado"] == "LIBERADO"
    assert segunda.json()["estado"] == "LIBERADO"

    # ASSERT — somente uma liberação e um evento histórico
    with Session(db) as sessao:
        liberacoes = sessao.scalars(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id,
                Liberacao.data == date(2026, 10, 20),
            )
        ).all()

        assert len(liberacoes) == 1

        liberacao = liberacoes[0]
        assert liberacao.estado == Estado.LIBERADO

        historicos = sessao.scalars(
            select(HistoricoLiberacao).where(
                HistoricoLiberacao.liberacao_id == liberacao.id
            )
        ).all()

        assert len(historicos) == 1
        assert historicos[0].tipo_acao == TipoAcao.LIBERACAO


def test_responsavel_nao_libera_aluno_sem_vinculo(
    client_db,
    criar_usuario,
    criar_responsavel,
    db,
):
    # ARRANGE — responsável cadastrado, mas sem vínculo
    criar_responsavel()

    # Administração cria um aluno com matrícula vigente
    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    ano_id = criar_ano(
        client_db,
        headers_admin,
        ano=2026,
    )

    turma_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano A",
    )

    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="SEM-VINC-001",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers_admin,
    )

    assert matricula.status_code == 201

    # Autenticar o responsável sem vínculo
    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    headers_responsavel = {
        "X-CSRF-Token": autenticacao.json()["csrf_token"]
    }

    # ACT — tentar liberar aluno não vinculado
    resposta = client_db.post(
        f"/responsavel/alunos/{aluno_id}/liberacao",
        json={"acao": "LIBERAR"},
        headers=headers_responsavel,
    )

    # ASSERT — operação não autorizada
    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Aluno nao encontrado."

    # ASSERT — nenhuma liberação ou histórico foi criado
    with Session(db) as sessao:
        liberacoes = sessao.scalars(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id,
            )
        ).all()

        historicos = sessao.scalars(
            select(HistoricoLiberacao).where(
                HistoricoLiberacao.aluno_id == aluno_id,
            )
        ).all()

        assert liberacoes == []
        assert historicos == []


def test_responsavel_nao_libera_aluno_com_vinculo_revogado(
    client_db,
    criar_usuario,
    criar_responsavel,
    relogio,
    db,
):
    # ARRANGE — responsável ativo
    responsavel_id = criar_responsavel()

    # Autenticar administrador
    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    # Ano letivo e turma existentes
    ano_id = criar_ano(
        client_db,
        headers_admin,
        ano=2026,
    )

    turma_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano A",
    )

    # Criar aluno e matrícula vigente
    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="VINC-REV-LIB-001",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers_admin,
    )
    assert matricula.status_code == 201

    # Criar vínculo vigente
    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert vinculo.status_code == 201

    vinculo_id = vinculo.json()["id"]

    # Avançar o relógio após a criação
    relogio.avancar(seconds=1)

    # Revogar o vínculo enquanto administrador
    revogado = client_db.post(
        f"/admin/vinculos/{vinculo_id}/revogar",
        headers=headers_admin,
    )

    assert revogado.status_code == 200
    assert revogado.json()["ativo"] is False

    # Autenticar como o responsável do vínculo revogado
    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    headers_responsavel = {
        "X-CSRF-Token": autenticacao.json()["csrf_token"]
    }

    # ACT — tentar liberar o aluno após a revogação
    resposta = client_db.post(
        f"/responsavel/alunos/{aluno_id}/liberacao",
        json={"acao": "LIBERAR"},
        headers=headers_responsavel,
    )

    # ASSERT — não existe mais autorização
    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Aluno nao encontrado."

    # ASSERT — tentativa não modifica os dados
    with Session(db) as sessao:
        liberacoes = sessao.scalars(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id,
            )
        ).all()

        historicos = sessao.scalars(
            select(HistoricoLiberacao).where(
                HistoricoLiberacao.aluno_id == aluno_id,
            )
        ).all()

        assert liberacoes == []
        assert historicos == []


def test_responsavel_nao_libera_apos_horario_limite(
    client_db,
    criar_usuario,
    criar_responsavel,
    relogio,
    db,
):
    # ARRANGE — responsável ativo
    responsavel_id = criar_responsavel()

    # Autenticar administrador
    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    # Criar ano letivo e turma da manhã
    ano_id = criar_ano(
        client_db,
        headers_admin,
        ano=2026,
    )

    turma_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano A",
    )

    # Criar aluno com matrícula vigente
    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="LIMITE-001",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers_admin,
    )
    assert matricula.status_code == 201

    # Criar vínculo vigente
    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert vinculo.status_code == 201

    # Avançar o relógio para o horário-limite.
    # 16h UTC = 13h no fuso America/Sao_Paulo.
    relogio.avancar(hours=6)

    # Autenticar o responsável no novo instante.
    # Assim, a sessão estará válida durante a tentativa.
    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )

    assert autenticacao.status_code == 200

    headers_responsavel = {
        "X-CSRF-Token": autenticacao.json()["csrf_token"]
    }

    # ACT — tentar liberar exatamente no horário-limite
    resposta = client_db.post(
        f"/responsavel/alunos/{aluno_id}/liberacao",
        json={"acao": "LIBERAR"},
        headers=headers_responsavel,
    )

    # ASSERT — horário-limite ultrapassado
    assert resposta.status_code == 409
    assert "Horario-limite" in resposta.json()["detail"]

    # ACT — tentar liberar exatamente no horário-limite
    resposta = client_db.post(
        f"/responsavel/alunos/{aluno_id}/liberacao",
        json={"acao": "LIBERAR"},
        headers=headers_responsavel,
    )

    # ASSERT — operação rejeitada pelo horário
    assert resposta.status_code == 409
    assert "Horario-limite" in resposta.json()["detail"]

    # ASSERT — nenhuma alteração persistida
    with Session(db) as sessao:
        liberacoes = sessao.scalars(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id,
            )
        ).all()

        historicos = sessao.scalars(
            select(HistoricoLiberacao).where(
                HistoricoLiberacao.aluno_id == aluno_id,
            )
        ).all()

        assert liberacoes == []
        assert historicos == []


def test_responsavel_cancela_liberacao_e_preserva_historico(
    client_db,
    criar_usuario,
    criar_responsavel,
    db,
):
    # ARRANGE — responsável e administrador
    responsavel_id = criar_responsavel()

    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    # Ano letivo e turma da manhã
    ano_id = criar_ano(
        client_db,
        headers_admin,
        ano=2026,
    )

    turma_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano A",
    )

    # Aluno matriculado na data simulada
    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="LIB-CANC-001",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers_admin,
    )
    assert matricula.status_code == 201

    # Vínculo ativo com o responsável
    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert vinculo.status_code == 201

    # Autenticação como responsável
    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    usuario_id = autenticacao.json()["usuario"]["id"]

    headers_responsavel = {
        "X-CSRF-Token": autenticacao.json()["csrf_token"]
    }

    url = f"/responsavel/alunos/{aluno_id}/liberacao"

    # ACT 1 — liberar o aluno
    primeira = client_db.post(
        url,
        json={"acao": "LIBERAR"},
        headers=headers_responsavel,
    )

    assert primeira.status_code == 200
    assert primeira.json()["estado"] == "LIBERADO"

    # ACT 2 — cancelar a liberação
    segunda = client_db.post(
        url,
        json={"acao": "CANCELAR"},
        headers=headers_responsavel,
    )

    # ASSERT — o estado atual foi alterado
    assert segunda.status_code == 200
    assert segunda.json()["estado"] == "CANCELADO"

    # ASSERT — persistência e histórico
    with Session(db) as sessao:
        liberacoes = sessao.scalars(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id,
                Liberacao.data == date(2026, 10, 20),
            )
        ).all()

        assert len(liberacoes) == 1

        liberacao = liberacoes[0]

        assert liberacao.estado == Estado.CANCELADO
        assert liberacao.atualizado_por_usuario_id == usuario_id

        eventos = sessao.scalars(
            select(HistoricoLiberacao)
            .where(
                HistoricoLiberacao.liberacao_id == liberacao.id
            )
            .order_by(HistoricoLiberacao.id)
        ).all()

        assert len(eventos) == 2

        primeiro, segundo = eventos

        # Evento original
        assert primeiro.estado_anterior is None
        assert primeiro.novo_estado == Estado.LIBERADO
        assert primeiro.tipo_acao == TipoAcao.LIBERACAO

        # Evento de cancelamento
        assert segundo.estado_anterior == Estado.LIBERADO
        assert segundo.novo_estado == Estado.CANCELADO
        assert segundo.tipo_acao == TipoAcao.CANCELAMENTO

        # Ambos atribuídos ao responsável autenticado
        assert primeiro.usuario_id == usuario_id
        assert segundo.usuario_id == usuario_id
        assert primeiro.perfil == Perfil.RESPONSAVEL
        assert segundo.perfil == Perfil.RESPONSAVEL


def test_responsavel_libera_novamente_apos_cancelamento(
    client_db,
    criar_usuario,
    criar_responsavel,
    db,
):
    # ARRANGE — responsável e estrutura escolar
    responsavel_id = criar_responsavel()

    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    ano_id = criar_ano(
        client_db,
        headers_admin,
        ano=2026,
    )

    turma_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano A",
    )

    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="LIB-RELIB-001",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers_admin,
    )
    assert matricula.status_code == 201

    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert vinculo.status_code == 201

    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    usuario_id = autenticacao.json()["usuario"]["id"]

    headers_responsavel = {
        "X-CSRF-Token": autenticacao.json()["csrf_token"]
    }

    url = f"/responsavel/alunos/{aluno_id}/liberacao"

    # ACT — LIBERAR → CANCELAR → LIBERAR
    primeira = client_db.post(
        url,
        json={"acao": "LIBERAR"},
        headers=headers_responsavel,
    )

    segunda = client_db.post(
        url,
        json={"acao": "CANCELAR"},
        headers=headers_responsavel,
    )

    terceira = client_db.post(
        url,
        json={"acao": "LIBERAR"},
        headers=headers_responsavel,
    )

    # ASSERT — três operações aceitas
    assert primeira.status_code == 200
    assert segunda.status_code == 200
    assert terceira.status_code == 200

    assert primeira.json()["estado"] == "LIBERADO"
    assert segunda.json()["estado"] == "CANCELADO"
    assert terceira.json()["estado"] == "LIBERADO"

    # ASSERT — estado atual e histórico persistidos
    with Session(db) as sessao:
        liberacoes = sessao.scalars(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id,
                Liberacao.data == date(2026, 10, 20),
            )
        ).all()

        assert len(liberacoes) == 1

        liberacao = liberacoes[0]

        assert liberacao.estado == Estado.LIBERADO
        assert liberacao.atualizado_por_usuario_id == usuario_id

        eventos = sessao.scalars(
            select(HistoricoLiberacao)
            .where(
                HistoricoLiberacao.liberacao_id == liberacao.id
            )
            .order_by(HistoricoLiberacao.id)
        ).all()

        assert len(eventos) == 3

        assert [
            (
                evento.estado_anterior,
                evento.novo_estado,
                evento.tipo_acao,
            )
            for evento in eventos
        ] == [
            (
                None,
                Estado.LIBERADO,
                TipoAcao.LIBERACAO,
            ),
            (
                Estado.LIBERADO,
                Estado.CANCELADO,
                TipoAcao.CANCELAMENTO,
            ),
            (
                Estado.CANCELADO,
                Estado.LIBERADO,
                TipoAcao.LIBERACAO,
            ),
        ]

        assert all(
            evento.usuario_id == usuario_id
            for evento in eventos
        )

        assert all(
            evento.perfil == Perfil.RESPONSAVEL
            for evento in eventos
        )


def test_falha_no_historico_reverte_liberacao(
    client_db,
    criar_usuario,
    criar_responsavel,
    db,
):
    # ARRANGE — preparar aluno, matrícula e vínculo.
    responsavel_id = criar_responsavel()

    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    ano_id = criar_ano(
        client_db,
        headers_admin,
        ano=2026,
    )

    turma_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano A",
    )

    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="ROLLBACK-001",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers_admin,
    )
    assert matricula.status_code == 201

    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert vinculo.status_code == 201

    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    headers_responsavel = {
        "X-CSRF-Token": autenticacao.json()["csrf_token"]
    }

    # Simular falha durante o flush do histórico.
    def falhar_persistencia_historico(
        sessao,
        flush_context,
        instances,
    ):
        if any(
            isinstance(objeto, HistoricoLiberacao)
            for objeto in sessao.new
        ):
            raise RuntimeError(
                "Falha simulada na persistencia do historico"
            )

    event.listen(
        Session,
        "before_flush",
        falhar_persistencia_historico,
    )

    try:
        # ACT — a API executa a liberação.
        # O TestClient propaga a exceção do servidor.
        with pytest.raises(
            RuntimeError,
            match="Falha simulada",
        ):
            client_db.post(
                f"/responsavel/alunos/{aluno_id}/liberacao",
                json={"acao": "LIBERAR"},
                headers=headers_responsavel,
            )
    finally:
        # Impedir interferência nos testes seguintes.
        event.remove(
            Session,
            "before_flush",
            falhar_persistencia_historico,
        )

    # ASSERT — nenhuma liberação persistiu.
    with Session(db) as sessao:
        liberacoes = sessao.scalars(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id,
            )
        ).all()

        historicos = sessao.scalars(
            select(HistoricoLiberacao).where(
                HistoricoLiberacao.aluno_id == aluno_id,
            )
        ).all()

        assert liberacoes == []
        assert historicos == []


def test_falha_no_historico_reverte_cancelamento(
    client_db,
    criar_usuario,
    criar_responsavel,
    db,
):
    # ARRANGE — cadastrar responsável e estrutura escolar
    responsavel_id = criar_responsavel()

    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    ano_id = criar_ano(
        client_db,
        headers_admin,
        ano=2026,
    )

    turma_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano A",
    )

    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="ROLLBACK-CANC-001",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers_admin,
    )
    assert matricula.status_code == 201

    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert vinculo.status_code == 201

    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    usuario_id = autenticacao.json()["usuario"]["id"]

    headers_responsavel = {
        "X-CSRF-Token": autenticacao.json()["csrf_token"]
    }

    url = f"/responsavel/alunos/{aluno_id}/liberacao"

    # 1. Criar uma liberação válida
    primeira = client_db.post(
        url,
        json={"acao": "LIBERAR"},
        headers=headers_responsavel,
    )

    assert primeira.status_code == 200
    assert primeira.json()["estado"] == "LIBERADO"

    # Confirmar o estado inicial antes de injetar a falha
    with Session(db) as sessao:
        liberacao = sessao.scalar(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id,
                Liberacao.data == date(2026, 10, 20),
            )
        )

        assert liberacao is not None
        assert liberacao.estado == Estado.LIBERADO

        liberacao_id = liberacao.id

        eventos = sessao.scalars(
            select(HistoricoLiberacao).where(
                HistoricoLiberacao.liberacao_id == liberacao_id
            )
        ).all()

        assert len(eventos) == 1
        evento_original_id = eventos[0].id

    # 2. Simular falha somente quando um novo
    # HistoricoLiberacao for persistido
    def falhar_persistencia_historico(
        sessao,
        flush_context,
        instances,
    ):
        if any(
            isinstance(objeto, HistoricoLiberacao)
            for objeto in sessao.new
        ):
            raise RuntimeError(
                "Falha simulada no historico do cancelamento"
            )

    event.listen(
        Session,
        "before_flush",
        falhar_persistencia_historico,
    )

    try:
        # ACT — solicitar cancelamento.
        # A exceção impede a confirmação da transação.
        with pytest.raises(
            RuntimeError,
            match="Falha simulada",
        ):
            client_db.post(
                url,
                json={"acao": "CANCELAR"},
                headers=headers_responsavel,
            )
    finally:
        # Evitar interferência em outros testes
        event.remove(
            Session,
            "before_flush",
            falhar_persistencia_historico,
        )

    # ASSERT — rollback preserva o estado anterior
    with Session(db) as sessao:
        liberacoes = sessao.scalars(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id,
                Liberacao.data == date(2026, 10, 20),
            )
        ).all()

        assert len(liberacoes) == 1

        liberacao = liberacoes[0]

        assert liberacao.id == liberacao_id
        assert liberacao.estado == Estado.LIBERADO
        assert liberacao.atualizado_por_usuario_id == usuario_id

        eventos = sessao.scalars(
            select(HistoricoLiberacao)
            .where(
                HistoricoLiberacao.liberacao_id == liberacao_id
            )
            .order_by(HistoricoLiberacao.id)
        ).all()

        assert len(eventos) == 1

        evento = eventos[0]

        assert evento.id == evento_original_id
        assert evento.estado_anterior is None
        assert evento.novo_estado == Estado.LIBERADO
        assert evento.tipo_acao == TipoAcao.LIBERACAO
        assert evento.usuario_id == usuario_id

def test_duas_liberacoes_simultaneas_nao_duplicam_historico(
    client_db,
    criar_usuario,
    criar_responsavel,
    db,
    relogio,
    settings_teste,
    monkeypatch,
):
    # ARRANGE — preparar a estrutura escolar existente.
    responsavel_id = criar_responsavel()

    headers_admin = autenticar_admin(
        client_db, criar_usuario
    )

    ano_id = criar_ano(
        client_db, headers_admin, ano=2026
    )

    turma_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano A",
    )

    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="CONC-LIB-001",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers_admin,
    )
    assert matricula.status_code == 201

    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert vinculo.status_code == 201

    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    usuario_id = autenticacao.json()["usuario"]["id"]

    # Instrumentação exclusiva do teste:
    # induzir sobreposição entre as operações.
    primeira_avaliando = Event()
    segunda_avaliando = Event()
    controle = Lock()
    chamadas = 0

    avaliar_original = servico_liberacoes.avaliar_operacao

    def avaliacao_controlada(pedido):
        nonlocal chamadas

        with controle:
            chamadas += 1
            numero = chamadas

        if numero == 1:
            primeira_avaliando.set()
            # Se a segunda operação já alcançou a
            # avaliação, ambas viram o estado anterior.
            # Com bloqueio de linha, a segunda aguardará
            # e este timeout permitirá a primeira concluir.
            segunda_avaliando.wait(timeout=2)

        elif numero == 2:
            segunda_avaliando.set()

        return avaliar_original(pedido)

    monkeypatch.setattr(
        servico_liberacoes,
        "avaliar_operacao",
        avaliacao_controlada,
    )

    def executar():
        # Uma Session independente por thread.
        with Session(db) as sessao:
            return executar_liberacao_responsavel(
                sessao,
                aluno_id=aluno_id,
                usuario_id=usuario_id,
                acao=Acao.LIBERAR,
                agora=relogio.agora(),
                settings=settings_teste,
            )

    # ACT — disparar duas operações concorrentes.
    with ThreadPoolExecutor(max_workers=2) as executor:
        primeiro = executor.submit(executar)

        assert primeira_avaliando.wait(timeout=10)

        segundo = executor.submit(executar)

        resultados = [
            primeiro.result(timeout=15),
            segundo.result(timeout=15),
        ]

    # ASSERT — ambas as operações terminam normalmente.
    assert len(resultados) == 2
    assert all(
        resultado.estado == Estado.LIBERADO
        for resultado in resultados
    )

    # ASSERT — somente uma mudança real de estado.
    with Session(db) as sessao:
        liberacoes = sessao.scalars(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id,
                Liberacao.data == date(2026, 10, 20),
            )
        ).all()

        assert len(liberacoes) == 1

        eventos = sessao.scalars(
            select(HistoricoLiberacao).where(
                HistoricoLiberacao.liberacao_id
                == liberacoes[0].id
            )
        ).all()

        assert len(eventos) == 1
        assert eventos[0].novo_estado == Estado.LIBERADO
        assert eventos[0].tipo_acao == TipoAcao.LIBERACAO


def test_liberacao_e_cancelamento_concorrentes_preservam_historico(
    client_db,
    criar_usuario,
    criar_responsavel,
    db,
    relogio,
    settings_teste,
    monkeypatch,
):
    # ARRANGE — preparar o aluno e seu responsável
    responsavel_id = criar_responsavel()

    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    ano_id = criar_ano(
        client_db,
        headers_admin,
        ano=2026,
    )

    turma_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano A",
    )

    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="CONC-CANCEL-001",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers_admin,
    )
    assert matricula.status_code == 201

    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert vinculo.status_code == 201

    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    usuario_id = autenticacao.json()["usuario"]["id"]

    # Controlar a ordem das duas operações
    primeira_em_avaliacao = Event()
    liberar_primeira = Event()

    avaliar_original = servico_liberacoes.avaliar_operacao

    def avaliacao_controlada(pedido):
        if pedido.acao == Acao.LIBERAR:
            primeira_em_avaliacao.set()

            if not liberar_primeira.wait(timeout=10):
                raise TimeoutError(
                    "Primeira operacao nao foi liberada."
                )

        return avaliar_original(pedido)

    monkeypatch.setattr(
        servico_liberacoes,
        "avaliar_operacao",
        avaliacao_controlada,
    )

    def executar(acao):
        # Uma Session independente por thread
        with Session(db) as sessao:
            return executar_liberacao_responsavel(
                sessao,
                aluno_id=aluno_id,
                usuario_id=usuario_id,
                acao=acao,
                agora=relogio.agora(),
                settings=settings_teste,
            )

    # ACT — executar operações concorrentes
    with ThreadPoolExecutor(max_workers=2) as executor:
        primeira = executor.submit(
            executar,
            Acao.LIBERAR,
        )

        try:
            assert primeira_em_avaliacao.wait(timeout=10)

            segunda = executor.submit(
                executar,
                Acao.CANCELAR,
            )

        finally:
            # Liberar A mesmo se o teste falhar,
            # evitando deixar a thread bloqueada.
            liberar_primeira.set()

        resultado_primeiro = primeira.result(timeout=15)
        resultado_segundo = segunda.result(timeout=15)

    # ASSERT — ambas as operações foram concluídas
    assert resultado_primeiro.estado == Estado.LIBERADO
    assert resultado_segundo.estado == Estado.CANCELADO

    # ASSERT — estado final e histórico
    with Session(db) as sessao:
        liberacoes = sessao.scalars(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id,
                Liberacao.data == date(2026, 10, 20),
            )
        ).all()

        assert len(liberacoes) == 1

        liberacao = liberacoes[0]
        assert liberacao.estado == Estado.CANCELADO
        assert liberacao.atualizado_por_usuario_id == usuario_id

        eventos = sessao.scalars(
            select(HistoricoLiberacao)
            .where(
                HistoricoLiberacao.liberacao_id == liberacao.id
            )
            .order_by(HistoricoLiberacao.id)
        ).all()

        assert len(eventos) == 2

        assert [
            (
                evento.estado_anterior,
                evento.novo_estado,
                evento.tipo_acao,
            )
            for evento in eventos
        ] == [
            (
                None,
                Estado.LIBERADO,
                TipoAcao.LIBERACAO,
            ),
            (
                Estado.LIBERADO,
                Estado.CANCELADO,
                TipoAcao.CANCELAMENTO,
            ),
        ]


def test_revogacao_aguarda_liberacao_em_andamento(
    client_db,
    criar_usuario,
    criar_responsavel,
    db,
    relogio,
    settings_teste,
    monkeypatch,
):
    # ARRANGE — responsável, aluno e matrícula vigente
    responsavel_id = criar_responsavel()

    headers_admin = autenticar_admin(
        client_db, criar_usuario
    )

    ano_id = criar_ano(
        client_db, headers_admin, ano=2026
    )

    turma_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano A",
    )

    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="CONC-REV-001",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers_admin,
    )
    assert matricula.status_code == 201

    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert vinculo.status_code == 201

    vinculo_id = vinculo.json()["id"]

    # Descobrir o Usuario.id do responsável existente
    with Session(db) as sessao:
        from app.models import Responsavel

        responsavel = sessao.get(
            Responsavel, responsavel_id
        )
        assert responsavel is not None
        usuario_id = responsavel.usuario_id

    # Respeitar a restrição temporal de revogação.
    relogio.avancar(seconds=1)

    # Instrumentação do teste
    liberacao_em_avaliacao = Event()
    permitir_liberacao = Event()

    avaliacao_original = (
        servico_liberacoes.avaliar_operacao
    )

    def avaliacao_controlada(pedido):
        liberacao_em_avaliacao.set()

        if not permitir_liberacao.wait(timeout=10):
            raise TimeoutError(
                "Liberação não foi desbloqueada."
            )

        return avaliacao_original(pedido)

    monkeypatch.setattr(
        servico_liberacoes,
        "avaliar_operacao",
        avaliacao_controlada,
    )

    def executar_liberacao():
        with Session(db) as sessao:
            return executar_liberacao_responsavel(
                sessao,
                aluno_id=aluno_id,
                usuario_id=usuario_id,
                acao=Acao.LIBERAR,
                agora=relogio.agora(),
                settings=settings_teste,
            )

    def executar_revogacao():
        return client_db.post(
            f"/admin/vinculos/{vinculo_id}/revogar",
            headers=headers_admin,
        )

    # ACT — duas transações independentes
    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_liberacao = executor.submit(
            executar_liberacao
        )

        try:
            assert liberacao_em_avaliacao.wait(
                timeout=10
            )

            futuro_revogacao = executor.submit(
                executar_revogacao
            )

            # Enquanto a liberação mantém seu bloqueio,
            # a revogação não deve conseguir concluir.
            with pytest.raises(FutureTimeoutError):
                futuro_revogacao.result(timeout=0.5)

        finally:
            # Liberar a primeira transação, mesmo
            # quando alguma asserção falhar.
            permitir_liberacao.set()

        resultado_liberacao = (
            futuro_liberacao.result(timeout=15)
        )

        resultado_revogacao = (
            futuro_revogacao.result(timeout=15)
        )

    # ASSERT — liberação seguida de revogação
    assert resultado_liberacao.estado == Estado.LIBERADO

    assert resultado_revogacao.status_code == 200
    assert resultado_revogacao.json()["ativo"] is False

    # ASSERT — a liberação confirmada é preservada
    with Session(db) as sessao:
        liberacoes = sessao.scalars(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id,
                Liberacao.data == date(2026, 10, 20),
            )
        ).all()

        assert len(liberacoes) == 1
        assert liberacoes[0].estado == Estado.LIBERADO

        eventos = sessao.scalars(
            select(HistoricoLiberacao).where(
                HistoricoLiberacao.liberacao_id
                == liberacoes[0].id
            )
        ).all()

        assert len(eventos) == 1
        assert eventos[0].tipo_acao == TipoAcao.LIBERACAO


def test_liberacao_aguarda_revogacao_e_e_rejeitada(
    client_db,
    criar_usuario,
    criar_responsavel,
    db,
    relogio,
    settings_teste,
):
    # ARRANGE — cadastros existentes
    responsavel_id = criar_responsavel()

    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    ano_id = criar_ano(
        client_db,
        headers_admin,
        ano=2026,
    )

    turma_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano A",
    )

    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="REV-PRIMEIRO-001",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers_admin,
    )
    assert matricula.status_code == 201

    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert vinculo.status_code == 201

    vinculo_id = vinculo.json()["id"]

    with Session(db) as sessao:
        from app.models import Responsavel

        responsavel = sessao.get(
            Responsavel,
            responsavel_id,
        )
        assert responsavel is not None
        usuario_id = responsavel.usuario_id

    # A revogação exige instante posterior à criação.
    relogio.avancar(seconds=1)

    revogacao_bloqueou = Event()
    permitir_revogacao = Event()
    controle = Lock()
    pausou = False

    # Instrumentação temporária do SQLAlchemy.
    def pausar_revogacao(sessao, flush_context, instances):
        nonlocal pausou

        # Ativar somente para a sessão que alterou
        # o vínculo, sem afetar outras transações.
        if not any(
            isinstance(objeto, ResponsavelAluno)
            and objeto.revogado_em is not None
            for objeto in sessao.dirty
        ):
            return

        with controle:
            if pausou:
                return
            pausou = True

        revogacao_bloqueou.set()

        if not permitir_revogacao.wait(timeout=10):
            raise TimeoutError(
                "Revogação não foi liberada."
            )

    event.listen(
        Session,
        "before_flush",
        pausar_revogacao,
    )

    def executar_revogacao():
        return client_db.post(
            f"/admin/vinculos/{vinculo_id}/revogar",
            headers=headers_admin,
        )

    def executar_liberacao():
        with Session(db) as sessao:
            return executar_liberacao_responsavel(
                sessao,
                aluno_id=aluno_id,
                usuario_id=usuario_id,
                acao=Acao.LIBERAR,
                agora=relogio.agora(),
                settings=settings_teste,
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_revogacao = executor.submit(
                executar_revogacao
            )

            try:
                assert revogacao_bloqueou.wait(timeout=10)

                futuro_liberacao = executor.submit(
                    executar_liberacao
                )

                # O responsável deve aguardar o bloqueio
                # mantido pela transação administrativa.
                with pytest.raises(FutureTimeoutError):
                    futuro_liberacao.result(timeout=0.5)

            finally:
                # Liberar a revogação mesmo em caso de falha.
                permitir_revogacao.set()

            resposta_revogacao = futuro_revogacao.result(
                timeout=15
            )

            try:
                futuro_liberacao.result(timeout=15)
                pytest.fail(
                    "Liberação indevida após revogação."
                )
            except Exception as exc:
                from fastapi import HTTPException

                assert isinstance(exc, HTTPException)
                assert exc.status_code == 404

    finally:
        permitir_revogacao.set()
        event.remove(
            Session,
            "before_flush",
            pausar_revogacao,
        )

    # ASSERT — revogação confirmada.
    assert resposta_revogacao.status_code == 200

    with Session(db) as sessao:
        vinculo_atual = sessao.get(
            ResponsavelAluno,
            vinculo_id,
        )
        assert vinculo_atual is not None
        assert vinculo_atual.revogado_em is not None

        liberacoes = sessao.scalars(
            select(Liberacao).where(
                Liberacao.aluno_id == aluno_id
            )
        ).all()

        historicos = sessao.scalars(
            select(HistoricoLiberacao).where(
                HistoricoLiberacao.aluno_id == aluno_id
            )
        ).all()

        assert liberacoes == []
        assert historicos == []


def test_fixture_cenario_liberacao_prepara_dados_validos(
    client_db,
    cenario_liberacao,
):
    # ARRANGE
    ctx = cenario_liberacao()

    assert isinstance(ctx["responsavel_id"], int)
    assert isinstance(ctx["aluno_id"], int)
    assert isinstance(ctx["vinculo_id"], int)

    # Confirmar que o vínculo foi criado.
    resposta = client_db.get(
        f"/admin/vinculos/{ctx['vinculo_id']}"
    )

    assert resposta.status_code == 200
    assert resposta.json()["aluno_id"] == ctx["aluno_id"]
    assert (
        resposta.json()["responsavel_id"]
        == ctx["responsavel_id"]
    )
