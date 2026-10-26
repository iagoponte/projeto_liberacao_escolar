
"""Testes das consultas administrativas de liberações."""

from tests.api.test_matriculas import (
    autenticar_admin,
    criar_aluno,
    criar_ano,
    criar_turma,
    payload_matricula,
)

from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Usuario, Liberacao
from app.domain.estados import Estado, Perfil


def test_admin_consulta_alunos_sem_registro_de_liberacao(
    client_db,
    criar_usuario,
):
    # ARRANGE — administrador autenticado
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
        matricula="LIB-ADMIN-001",
    )

    resposta_matricula = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id,
            turma_id,
            ano_id,
            inicio="2026-02-01",
        ),
        headers=headers,
    )

    assert resposta_matricula.status_code == 201

    # ACT — consultar situação de liberação
    resposta = client_db.get(
        "/admin/liberacoes",
        params={
            "turma_id": turma_id,
            "data": "2026-10-20",
        },
        headers=headers,
    )

    # ASSERT — contrato HTTP
    assert resposta.status_code == 200

    dados = resposta.json()

    assert isinstance(dados, list)
    assert len(dados) == 1

    aluno = dados[0]

    assert aluno["aluno_id"] == aluno_id
    assert isinstance(aluno["nome_completo"], str)
    assert aluno["matricula_institucional"] == "LIB-ADMIN-001"
    assert aluno["turma_id"] == turma_id
    assert aluno["data"] == "2026-10-20"
    assert aluno["estado"] == "SEM_REGISTRO"


def test_admin_consulta_tres_estados_de_liberacao(
    client_db,
    criar_usuario,
    db,
):
    # ARRANGE — administração
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

    alunos = {}

    for nome, matricula in [
        ("A", "LIB-ESTADO-001"),
        ("B", "LIB-ESTADO-002"),
        ("C", "LIB-ESTADO-003"),
    ]:
        aluno_id = criar_aluno(
            client_db,
            headers,
            matricula=matricula,
        )

        resposta = client_db.post(
            "/admin/matriculas",
            json=payload_matricula(
                aluno_id,
                turma_id,
                ano_id,
                inicio="2026-02-01",
            ),
            headers=headers,
        )

        assert resposta.status_code == 201
        alunos[nome] = aluno_id

    # Criar estados de liberação diretamente no banco.
    # Aqui estamos testando a consulta administrativa,
    # não o fluxo de criação da liberação.
    with Session(db) as sessao:
        sessao.add_all([
            Liberacao(
                aluno_id=alunos["A"],
                data=date(2026, 10, 20),
                estado=Estado.LIBERADO,
                atualizado_por_usuario_id=1,
            ),
            Liberacao(
                aluno_id=alunos["B"],
                data=date(2026, 10, 20),
                estado=Estado.CANCELADO,
                atualizado_por_usuario_id=1,
            ),
        ])

        sessao.commit()

    # ACT — consultar o dia com liberações.
    resposta = client_db.get(
        "/admin/liberacoes",
        params={
            "turma_id": turma_id,
            "data": "2026-10-20",
        },
        headers=headers,
    )

    assert resposta.status_code == 200

    resultado = {
        item["aluno_id"]: item["estado"]
        for item in resposta.json()
    }

    # ASSERT — estados corretos
    assert resultado == {
        alunos["A"]: "LIBERADO",
        alunos["B"]: "CANCELADO",
        alunos["C"]: "SEM_REGISTRO",
    }

    # ACT — consultar outra data.
    outra_data = client_db.get(
        "/admin/liberacoes",
        params={
            "turma_id": turma_id,
            "data": "2026-10-21",
        },
        headers=headers,
    )

    assert outra_data.status_code == 200

    estados_outra_data = {
        item["aluno_id"]: item["estado"]
        for item in outra_data.json()
    }

    # Nenhum dos alunos possui liberação nesse dia.
    assert estados_outra_data == {
        alunos["A"]: "SEM_REGISTRO",
        alunos["B"]: "SEM_REGISTRO",
        alunos["C"]: "SEM_REGISTRO",
    }


def test_admin_filtra_alunos_por_estado(
    client_db,
    criar_usuario,
    db,
):
    headers = autenticar_admin(client_db, criar_usuario)

    ano_id = criar_ano(client_db, headers, ano=2026)

    turma_id = criar_turma(
        client_db,
        headers,
        ano_id,
        identificacao="1 Ano A",
    )

    alunos = {}

    for chave, matricula in [
        ("liberado", "FILTRO-001"),
        ("cancelado", "FILTRO-002"),
        ("sem_registro", "FILTRO-003"),
    ]:
        aluno_id = criar_aluno(
            client_db,
            headers,
            matricula=matricula,
        )

        resposta = client_db.post(
            "/admin/matriculas",
            json=payload_matricula(
                aluno_id,
                turma_id,
                ano_id,
                inicio="2026-02-01",
            ),
            headers=headers,
        )

        assert resposta.status_code == 201
        alunos[chave] = aluno_id

    with Session(db) as sessao:
        admin_id = sessao.scalar(
            select(Usuario.id).where(
                Usuario.perfil == Perfil.ADMIN
            )
        )
        assert admin_id is not None

        sessao.add_all([
            Liberacao(
                aluno_id=alunos["liberado"],
                data=date(2026, 10, 20),
                estado=Estado.LIBERADO,
                atualizado_por_usuario_id=admin_id,
            ),
            Liberacao(
                aluno_id=alunos["cancelado"],
                data=date(2026, 10, 20),
                estado=Estado.CANCELADO,
                atualizado_por_usuario_id=admin_id,
            ),
        ])
        sessao.commit()

    # Filtrar LIBERADO
    resposta = client_db.get(
        "/admin/liberacoes",
        params={
            "turma_id": turma_id,
            "data": "2026-10-20",
            "estado": "LIBERADO",
        },
        headers=headers,
    )

    assert resposta.status_code == 200
    assert [
        item["aluno_id"] for item in resposta.json()
    ] == [alunos["liberado"]]

    # Filtrar CANCELADO
    resposta = client_db.get(
        "/admin/liberacoes",
        params={
            "turma_id": turma_id,
            "data": "2026-10-20",
            "estado": "CANCELADO",
        },
        headers=headers,
    )

    assert resposta.status_code == 200
    assert [
        item["aluno_id"] for item in resposta.json()
    ] == [alunos["cancelado"]]

    # Filtrar SEM_REGISTRO
    resposta = client_db.get(
        "/admin/liberacoes",
        params={
            "turma_id": turma_id,
            "data": "2026-10-20",
            "estado": "SEM_REGISTRO",
        },
        headers=headers,
    )

    assert resposta.status_code == 200
    assert [
        item["aluno_id"] for item in resposta.json()
    ] == [alunos["sem_registro"]]


def test_admin_pesquisa_aluno_por_matricula(
    client_db,
    criar_usuario,
):
    headers = autenticar_admin(client_db, criar_usuario)

    ano_id = criar_ano(client_db, headers, ano=2026)

    turma_id = criar_turma(
        client_db,
        headers,
        ano_id,
        identificacao="1 Ano A",
    )

    for matricula in [
        "BUSCA-ABC-001",
        "BUSCA-XYZ-002",
    ]:
        aluno_id = criar_aluno(
            client_db,
            headers,
            matricula=matricula,
        )

        resposta = client_db.post(
            "/admin/matriculas",
            json=payload_matricula(
                aluno_id,
                turma_id,
                ano_id,
                inicio="2026-02-01",
            ),
            headers=headers,
        )

        assert resposta.status_code == 201

    resposta = client_db.get(
        "/admin/liberacoes",
        params={
            "turma_id": turma_id,
            "data": "2026-10-20",
            "busca": "abc",
        },
        headers=headers,
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert len(dados) == 1
    assert dados[0]["matricula_institucional"] == "BUSCA-ABC-001"
