
"""E6.1 — Testes de integração da agenda escolar."""

import pytest

from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.api.conftest import login

from app.models import EventoAgenda
from tests.api.test_matriculas import (
    autenticar_admin,
    criar_ano,
    criar_turma,
    criar_aluno,
    payload_matricula,
)

from tests.api.test_vinculos import criar_vinculo

pytestmark = pytest.mark.integration

URL_EVENTOS = "/admin/eventos"


def test_admin_cadastra_evento_escolar(
    client_db,
    criar_usuario,
    db,
):
    # ARRANGE — administrador autenticado
    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    # Criar ano letivo e turma
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

    # Dados do evento
    dados = {
        "turma_id": turma_id,
        "titulo": "Reuniao de responsaveis",
        "data_inicio": "2026-11-10",
        "data_fim": "2026-11-10",
    }

    # ACT — cadastrar evento
    resposta = client_db.post(
        URL_EVENTOS,
        json=dados,
        headers=headers_admin,
    )

    # ASSERT — contrato HTTP
    assert resposta.status_code == 201

    corpo = resposta.json()

    assert isinstance(corpo["id"], int)
    assert corpo["turma_id"] == turma_id
    assert corpo["titulo"] == dados["titulo"]
    assert corpo["data_inicio"] == dados["data_inicio"]
    assert corpo["data_fim"] == dados["data_fim"]
    assert corpo["ativo"] is True

    # ASSERT — persistência real no PostgreSQL
    with Session(db) as sessao:
        evento = sessao.get(
            EventoAgenda,
            corpo["id"],
        )

        assert evento is not None
        assert evento.turma_id == turma_id
        assert evento.titulo == dados["titulo"]
        assert evento.data_inicio.isoformat() == "2026-11-10"
        assert evento.data_fim.isoformat() == "2026-11-10"
        assert evento.ativo is True


def test_admin_nao_cadastra_evento_com_periodo_invalido(
    client_db,
    criar_usuario,
    db,
):
    # ARRANGE — autenticação administrativa
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

    # Data final anterior à data inicial
    dados = {
        "turma_id": turma_id,
        "titulo": "Evento com periodo invalido",
        "data_inicio": "2026-11-15",
        "data_fim": "2026-11-10",
    }

    # ACT
    resposta = client_db.post(
        "/admin/eventos",
        json=dados,
        headers=headers_admin,
    )

    # ASSERT — rejeição controlada
    assert resposta.status_code == 422

    # ASSERT — nenhum registro foi persistido
    with Session(db) as sessao:
        eventos = sessao.scalars(
            select(EventoAgenda).where(
                EventoAgenda.turma_id == turma_id,
                EventoAgenda.titulo == dados["titulo"],
            )
        ).all()

        assert eventos == []


def test_admin_lista_eventos_ativos_por_turma(
    client_db,
    criar_usuario,
):
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

    eventos = [
        {
            "turma_id": turma_id,
            "titulo": "Feira de ciencias",
            "data_inicio": "2026-11-20",
            "data_fim": "2026-11-20",
        },
        {
            "turma_id": turma_id,
            "titulo": "Reuniao de responsaveis",
            "data_inicio": "2026-11-10",
            "data_fim": "2026-11-10",
        },
    ]

    for dados in eventos:
        resposta = client_db.post(
            "/admin/eventos",
            json=dados,
            headers=headers,
        )
        assert resposta.status_code == 201

    resposta = client_db.get(
        "/admin/eventos",
        params={"turma_id": turma_id},
        headers=headers,
    )

    assert resposta.status_code == 200

    resultado = resposta.json()

    assert isinstance(resultado, list)
    assert len(resultado) == 2

    # A API deve ordenar cronologicamente.
    assert [
        evento["titulo"] for evento in resultado
    ] == [
        "Reuniao de responsaveis",
        "Feira de ciencias",
    ]


def test_admin_consulta_evento_por_id(
    client_db,
    criar_usuario,
):
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

    criado = client_db.post(
        "/admin/eventos",
        json={
            "turma_id": turma_id,
            "titulo": "Visita ao museu",
            "data_inicio": "2026-11-12",
            "data_fim": "2026-11-12",
        },
        headers=headers,
    )

    assert criado.status_code == 201

    evento_id = criado.json()["id"]

    resposta = client_db.get(
        f"/admin/eventos/{evento_id}",
        headers=headers,
    )

    assert resposta.status_code == 200

    evento = resposta.json()

    assert evento["id"] == evento_id
    assert evento["turma_id"] == turma_id
    assert evento["titulo"] == "Visita ao museu"
    assert evento["ativo"] is True

def test_admin_edita_evento_escolar(
    client_db,
    criar_usuario,
    db,
):
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

    criado = client_db.post(
        "/admin/eventos",
        json={
            "turma_id": turma_id,
            "titulo": "Reuniao inicial",
            "data_inicio": "2026-11-10",
            "data_fim": "2026-11-10",
        },
        headers=headers,
    )

    assert criado.status_code == 201
    evento_id = criado.json()["id"]

    resposta = client_db.patch(
        f"/admin/eventos/{evento_id}",
        json={
            "titulo": "Reuniao remarcada",
            "data_inicio": "2026-11-15",
            "data_fim": "2026-11-16",
        },
        headers=headers,
    )

    assert resposta.status_code == 200

    dados = resposta.json()
    assert dados["titulo"] == "Reuniao remarcada"
    assert dados["data_inicio"] == "2026-11-15"
    assert dados["data_fim"] == "2026-11-16"
    assert dados["turma_id"] == turma_id
    assert dados["ativo"] is True

    with Session(db) as sessao:
        evento = sessao.get(EventoAgenda, evento_id)
        assert evento is not None
        assert evento.titulo == "Reuniao remarcada"
        assert evento.data_inicio.isoformat() == "2026-11-15"
        assert evento.data_fim.isoformat() == "2026-11-16"


def test_admin_desativa_evento_sem_excluir_registro(
    client_db,
    criar_usuario,
    db,
):
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

    criado = client_db.post(
        "/admin/eventos",
        json={
            "turma_id": turma_id,
            "titulo": "Feira cultural",
            "data_inicio": "2026-11-20",
            "data_fim": "2026-11-20",
        },
        headers=headers,
    )

    assert criado.status_code == 201
    evento_id = criado.json()["id"]

    resposta = client_db.delete(
        f"/admin/eventos/{evento_id}",
        headers=headers,
    )

    assert resposta.status_code == 204
    assert resposta.content == b""

    # O evento deixa de ser consultável pela API.
    consulta = client_db.get(
        f"/admin/eventos/{evento_id}",
        headers=headers,
    )
    assert consulta.status_code == 404

    # Mas permanece no banco, marcado como inativo.
    with Session(db) as sessao:
        evento = sessao.get(EventoAgenda, evento_id)
        assert evento is not None
        assert evento.ativo is False


def test_admin_filtra_eventos_por_sobreposicao_de_periodo(
    client_db,
    criar_usuario,
):
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

    cenarios = [
        # Começa antes do filtro e termina dentro.
        ("Evento A", "2026-11-08", "2026-11-12"),

        # Inteiramente dentro do filtro.
        ("Evento B", "2026-11-14", "2026-11-16"),

        # Começa dentro e termina depois.
        ("Evento C", "2026-11-19", "2026-11-24"),

        # Termina antes do filtro.
        ("Evento D", "2026-11-01", "2026-11-09"),

        # Começa depois do filtro.
        ("Evento E", "2026-11-21", "2026-11-25"),

        # Abrange todo o período consultado.
        ("Evento F", "2026-11-01", "2026-11-30"),
    ]

    for titulo, inicio, fim in cenarios:
        resposta = client_db.post(
            "/admin/eventos",
            json={
                "turma_id": turma_id,
                "titulo": titulo,
                "data_inicio": inicio,
                "data_fim": fim,
            },
            headers=headers,
        )
        assert resposta.status_code == 201

    # ACT — consultar de 10/11 a 20/11.
    resposta = client_db.get(
        "/admin/eventos",
        params={
            "turma_id": turma_id,
            "data_inicio": "2026-11-10",
            "data_fim": "2026-11-20",
        },
        headers=headers,
    )

    assert resposta.status_code == 200

    titulos = [
        evento["titulo"]
        for evento in resposta.json()
    ]

    # A ordenação segue a data de início.
    assert titulos == [
        "Evento F",
        "Evento A",
        "Evento B",
        "Evento C",
    ]


def test_responsavel_consulta_agenda_da_turma_do_seu_aluno(
    client_db,
    criar_usuario,
    criar_responsavel,
):
    # ARRANGE — administração
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
        matricula="AGENDA-001",
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

    responsavel_id = criar_responsavel()

    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )

    assert vinculo.status_code == 201

    evento = client_db.post(
        "/admin/eventos",
        json={
            "turma_id": turma_id,
            "titulo": "Feira de ciencias",
            "data_inicio": "2026-11-10",
            "data_fim": "2026-11-10",
        },
        headers=headers_admin,
    )

    assert evento.status_code == 201
    evento_id = evento.json()["id"]

    # Autenticar como responsável
    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )

    assert autenticacao.status_code == 200

    # ACT — consultar a agenda
    resposta = client_db.get(
        "/responsavel/agenda",
        params={
            "data_inicio": "2026-11-01",
            "data_fim": "2026-11-30",
        },
    )

    # ASSERT
    assert resposta.status_code == 200

    eventos = resposta.json()

    assert len(eventos) == 1
    assert eventos[0]["id"] == evento_id
    assert eventos[0]["titulo"] == "Feira de ciencias"
    assert eventos[0]["turma_id"] == turma_id


def test_responsavel_nao_visualiza_eventos_de_turma_sem_vinculo(
    client_db,
    criar_usuario,
    criar_responsavel,
):
    # ARRANGE — administrador
    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    ano_id = criar_ano(
        client_db,
        headers_admin,
        ano=2026,
    )

    # Turma do aluno vinculado
    turma_a_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano A",
    )

    # Outra turma, sem vínculo com o responsável
    turma_b_id = criar_turma(
        client_db,
        headers_admin,
        ano_id,
        identificacao="1 Ano B",
    )

    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="AGENDA-ISOLAMENTO-001",
    )

    matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_a_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers_admin,
    )
    assert matricula.status_code == 201

    responsavel_id = criar_responsavel()

    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert vinculo.status_code == 201

    # Um evento de cada turma
    for turma_id, titulo in [
        (turma_a_id, "Evento autorizado"),
        (turma_b_id, "Evento de outra turma"),
    ]:
        resposta = client_db.post(
            "/admin/eventos",
            json={
                "turma_id": turma_id,
                "titulo": titulo,
                "data_inicio": "2026-11-10",
                "data_fim": "2026-11-10",
            },
            headers=headers_admin,
        )
        assert resposta.status_code == 201

    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    # ACT
    resposta = client_db.get(
        "/responsavel/agenda",
        params={
            "data_inicio": "2026-11-01",
            "data_fim": "2026-11-30",
        },
    )

    # ASSERT
    assert resposta.status_code == 200

    eventos = resposta.json()

    assert len(eventos) == 1
    assert eventos[0]["titulo"] == "Evento autorizado"
    assert eventos[0]["turma_id"] == turma_a_id



def test_responsavel_nao_visualiza_agenda_apos_revogacao(
    client_db,
    criar_usuario,
    criar_responsavel,
    relogio,
):
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
        matricula="AGENDA-REVOGACAO-001",
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

    responsavel_id = criar_responsavel()

    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert vinculo.status_code == 201

    vinculo_id = vinculo.json()["id"]

    evento = client_db.post(
        "/admin/eventos",
        json={
            "turma_id": turma_id,
            "titulo": "Reuniao escolar",
            "data_inicio": "2026-11-10",
            "data_fim": "2026-11-10",
        },
        headers=headers_admin,
    )
    assert evento.status_code == 201

    # ACT — revogar o vínculo
    relogio.avancar(seconds=1)

    revogacao = client_db.post(
        f"/admin/vinculos/{vinculo_id}/revogar",
        headers=headers_admin,
    )

    assert revogacao.status_code == 200

    # Login após a revogação
    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    resposta = client_db.get(
        "/responsavel/agenda",
        params={
            "data_inicio": "2026-11-01",
            "data_fim": "2026-11-30",
        },
    )

    # ASSERT — o evento não pode mais ser visualizado
    assert resposta.status_code == 200
    assert resposta.json() == []
