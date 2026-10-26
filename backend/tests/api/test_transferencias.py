
"""E5.2-C — Testes de integração de transferências."""

import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.matriculas import transferir_matricula
from app.models import Matricula
from app.schemas.matriculas import TransferenciaCriar
from datetime import date
from unittest.mock import patch
from sqlalchemy import select

from tests.api.test_matriculas import (
    autenticar_admin,
    criar_ano,
    criar_turma,
    criar_aluno,
    matricular,
)

pytestmark = pytest.mark.integration

URL = "/admin/matriculas"


@pytest.fixture
def contexto_transferencia(client_db, criar_usuario):
    headers = autenticar_admin(client_db, criar_usuario)

    ano_id = criar_ano(client_db, headers, ano=2027)

    turma_origem_id = criar_turma(
        client_db,
        headers,
        ano_id,
        identificacao="1 Ano A",
    )

    turma_destino_id = criar_turma(
        client_db,
        headers,
        ano_id,
        identificacao="1 Ano B",
    )

    aluno_id = criar_aluno(client_db, headers)

    contexto = {
        "headers": headers,
        "ano_id": ano_id,
        "turma_id": turma_origem_id,
        "turma_destino_id": turma_destino_id,
        "aluno_id": aluno_id,
    }

    resposta = matricular(client_db, contexto)
    assert resposta.status_code == 201

    contexto["matricula_id"] = resposta.json()["id"]

    return contexto


def transferir(
    client_db,
    contexto,
    **alteracoes,
):
    dados = {
        "turma_destino_id": contexto["turma_destino_id"],
        "data_transferencia": "2027-04-15",
    }
    dados.update(alteracoes)

    return client_db.post(
        f"{URL}/{contexto['matricula_id']}/transferir",
        json=dados,
        headers=contexto["headers"],
    )


def test_admin_transfere_matricula_aberta(
    client_db,
    contexto_transferencia,
):
    contexto = contexto_transferencia

    resposta = transferir(client_db, contexto)

    assert resposta.status_code == 201

    dados = resposta.json()
    anterior = dados["matricula_anterior"]
    nova = dados["nova_matricula"]

    assert anterior["id"] == contexto["matricula_id"]
    assert anterior["data_fim"] == "2027-04-14"

    assert nova["id"] != anterior["id"]
    assert nova["aluno_id"] == contexto["aluno_id"]
    assert nova["turma_id"] == contexto["turma_destino_id"]
    assert nova["ano_letivo_id"] == contexto["ano_id"]
    assert nova["data_inicio"] == "2027-04-15"
    assert nova["data_fim"] is None


def test_nao_transfere_matricula_encerrada(
    client_db, contexto_transferencia
):
    ctx = contexto_transferencia

    encerramento = client_db.patch(
        f"{URL}/{ctx['matricula_id']}",
        json={"data_fim": "2027-04-10"},
        headers=ctx["headers"],
    )
    assert encerramento.status_code == 200

    resposta = transferir(client_db, ctx)

    assert resposta.status_code == 409


def test_nao_transfere_para_turma_inativa(
    client_db, contexto_transferencia
):
    ctx = contexto_transferencia

    alteracao = client_db.patch(
        f"/admin/turmas/{ctx['turma_destino_id']}",
        json={"ativo": False},
        headers=ctx["headers"],
    )
    assert alteracao.status_code == 200

    resposta = transferir(client_db, ctx)

    assert resposta.status_code == 409


def test_nao_transfere_para_outro_ano_letivo(
    client_db, contexto_transferencia
):
    ctx = contexto_transferencia

    outro_ano = criar_ano(
        client_db, ctx["headers"], ano=2028
    )
    outra_turma = criar_turma(
        client_db,
        ctx["headers"],
        outro_ano,
        identificacao="2 Ano A",
    )

    resposta = transferir(
        client_db,
        ctx,
        turma_destino_id=outra_turma,
    )

    assert resposta.status_code == 409


def test_nao_transfere_para_mesma_turma(
    client_db, contexto_transferencia
):
    ctx = contexto_transferencia

    resposta = transferir(
        client_db,
        ctx,
        turma_destino_id=ctx["turma_id"],
    )

    assert resposta.status_code == 409


@pytest.mark.parametrize(
    "data_transferencia",
    ["2027-02-01", "2027-01-31"],
)
def test_rejeita_transferencia_antes_ou_no_inicio(
    client_db,
    contexto_transferencia,
    data_transferencia,
):
    resposta = transferir(
        client_db,
        contexto_transferencia,
        data_transferencia=data_transferencia,
    )

    assert resposta.status_code == 422


def test_transferencia_recusada_preserva_matricula(
    client_db, contexto_transferencia
):
    ctx = contexto_transferencia

    resposta = transferir(
        client_db,
        ctx,
        turma_destino_id=ctx["turma_id"],
    )
    assert resposta.status_code == 409

    consulta = client_db.get(
        f"{URL}/{ctx['matricula_id']}"
    )

    assert consulta.status_code == 200
    assert consulta.json()["data_fim"] is None

    listagem = client_db.get(
        URL,
        params={
            "aluno_id": ctx["aluno_id"],
            "ano_letivo_id": ctx["ano_id"],
        },
    )

    assert listagem.status_code == 200
    assert len(listagem.json()) == 1


def test_transferencia_preserva_historico(
    client_db, contexto_transferencia
):
    ctx = contexto_transferencia

    resposta = transferir(client_db, ctx)
    assert resposta.status_code == 201

    listagem = client_db.get(
        URL,
        params={
            "aluno_id": ctx["aluno_id"],
            "ano_letivo_id": ctx["ano_id"],
        },
    )

    assert listagem.status_code == 200

    registros = {
        item["id"]: item
        for item in listagem.json()
    }

    assert len(registros) == 2

    anterior = registros[ctx["matricula_id"]]
    assert anterior["turma_id"] == ctx["turma_id"]
    assert anterior["data_inicio"] == "2027-02-01"
    assert anterior["data_fim"] == "2027-04-14"

    nova = resposta.json()["nova_matricula"]
    assert nova["id"] in registros
    assert nova["data_inicio"] == "2027-04-15"
    assert nova["data_fim"] is None


@pytest.mark.parametrize(
    "data_transferencia, fim_anterior",
    [
        ("2027-03-01", "2027-02-28"),
        ("2030-08-15", "2030-08-14"),
    ],
)
def test_permite_transferencia_retroativa_ou_futura(
    client_db,
    contexto_transferencia,
    data_transferencia,
    fim_anterior,
):
    resposta = transferir(
        client_db,
        contexto_transferencia,
        data_transferencia=data_transferencia,
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert (
        dados["matricula_anterior"]["data_fim"]
        == fim_anterior
    )
    assert (
        dados["nova_matricula"]["data_inicio"]
        == data_transferencia
    )


from app.domain.estados import Perfil
from tests.api.conftest import login


def test_sem_autenticacao_nao_transfere(client_db):
    resposta = client_db.post(
        f"{URL}/999999/transferir",
        json={
            "turma_destino_id": 2,
            "data_transferencia": "2027-04-15",
        },
    )

    assert resposta.status_code == 401


def test_responsavel_nao_transfere(
    client_db, criar_usuario
):
    criar_usuario(perfil=Perfil.RESPONSAVEL)

    autenticacao = login(client_db)
    assert autenticacao.status_code == 200

    resposta = client_db.post(
        f"{URL}/999999/transferir",
        json={
            "turma_destino_id": 2,
            "data_transferencia": "2027-04-15",
        },
        headers={
            "X-CSRF-Token":
                autenticacao.json()["csrf_token"]
        },
    )

    assert resposta.status_code == 403


def test_admin_sem_csrf_nao_transfere(
    client_db, contexto_transferencia
):
    ctx = contexto_transferencia

    resposta = client_db.post(
        f"{URL}/{ctx['matricula_id']}/transferir",
        json={
            "turma_destino_id": ctx["turma_destino_id"],
            "data_transferencia": "2027-04-15",
        },
    )

    assert resposta.status_code == 403


def test_falha_na_transferencia_preserva_estado_original(
    client_db,
    contexto_transferencia,
):
    ctx = contexto_transferencia

    # Cria um período histórico encerrado antes
    # da matrícula de origem, sem sobreposição.
    historica = matricular(
        client_db,
        ctx,
        data_inicio="2027-01-01",
        data_fim="2027-01-31",
    )

    # A matrícula aberta já foi criada pela fixture,
    # então esta inserção é temporalmente válida.
    assert historica.status_code == 201

    # Tenta transferir a matrícula aberta para uma
    # data anterior ao seu próprio início.
    resposta = transferir(
        client_db,
        ctx,
        data_transferencia="2027-01-15",
    )

    assert resposta.status_code == 422

    # A matrícula original deve continuar aberta.
    consulta = client_db.get(
        f"{URL}/{ctx['matricula_id']}"
    )

    assert consulta.status_code == 200
    assert consulta.json()["data_fim"] is None


def test_nao_transfere_aluno_inativo(
    client_db,
    contexto_transferencia,
):
    ctx = contexto_transferencia

    alteracao = client_db.patch(
        f"/admin/alunos/{ctx['aluno_id']}",
        json={"ativo": False},
        headers=ctx["headers"],
    )
    assert alteracao.status_code == 200

    resposta = transferir(client_db, ctx)

    assert resposta.status_code == 409

    consulta = client_db.get(
        f"{URL}/{ctx['matricula_id']}"
    )
    assert consulta.json()["data_fim"] is None


def test_nao_transfere_ano_letivo_inativo(
    client_db,
    contexto_transferencia,
):
   
    ctx = contexto_transferencia

    alteracao = client_db.patch(
        f"/admin/anos-letivos/{ctx['ano_id']}",
        json={"ativo": False},
        headers=ctx["headers"],
    )
    assert alteracao.status_code == 200

    resposta = transferir(client_db, ctx)

    assert resposta.status_code == 409

    consulta = client_db.get(
        f"{URL}/{ctx['matricula_id']}"
    )
    assert consulta.json()["data_fim"] is None


def test_nao_permite_transferir_duas_vezes_mesma_matricula(
    client_db,
    contexto_transferencia,
):
    ctx = contexto_transferencia

    primeira = transferir(
        client_db,
        ctx,
        data_transferencia="2027-04-15",
    )

    assert primeira.status_code == 201

    segunda = transferir(
        client_db,
        ctx,
        data_transferencia="2027-05-10",
    )

    assert segunda.status_code == 409

    consulta = client_db.get(
        f"{URL}/{ctx['matricula_id']}"
    )

    assert consulta.status_code == 200
    assert consulta.json()["data_fim"] == "2027-04-14"

    listagem = client_db.get(
        URL,
        params={
            "aluno_id": ctx["aluno_id"],
            "ano_letivo_id": ctx["ano_id"],
        },
    )

    assert listagem.status_code == 200
    assert len(listagem.json()) == 2



def test_transferencias_concorrentes_mesma_matricula(
    client_db,
    contexto_transferencia,
    db,
):
    ctx = contexto_transferencia

    # Terceira turma, para que cada transferência
    # tenha um destino diferente.
    terceira_turma_id = criar_turma(
        client_db,
        ctx["headers"],
        ctx["ano_id"],
        identificacao="1 Ano C",
    )

    barreira = Barrier(2, timeout=10)

    def executar_transferencia(turma_id, data_transferencia):
        with Session(db) as sessao:
            dados = TransferenciaCriar(
                turma_destino_id=turma_id,
                data_transferencia=data_transferencia,
            )

            # As duas threads ficam prontas antes
            # de chamar a regra de transferência.
            barreira.wait()

            try:
                transferir_matricula(
                    matricula_id=ctx["matricula_id"],
                    dados=dados,
                    db=sessao,
                )
                return "confirmada"

            except HTTPException as exc:
                sessao.rollback()

                if exc.status_code == 409:
                    return "conflito"

                raise

    with ThreadPoolExecutor(max_workers=2) as executor:
        primeira = executor.submit(
            executar_transferencia,
            ctx["turma_destino_id"],
            "2027-04-15",
        )
        segunda = executor.submit(
            executar_transferencia,
            terceira_turma_id,
            "2027-05-10",
        )

        resultados = [
            primeira.result(timeout=20),
            segunda.result(timeout=20),
        ]

    assert sorted(resultados) == [
        "confirmada",
        "conflito",
    ]

    with Session(db) as sessao:
        matriculas = (
            sessao.query(Matricula)
            .filter(
                Matricula.aluno_id == ctx["aluno_id"],
                Matricula.ano_letivo_id == ctx["ano_id"],
            )
            .all()
        )

        assert len(matriculas) == 2

        abertas = [
            matricula
            for matricula in matriculas
            if matricula.data_fim is None
        ]

        assert len(abertas) == 1
        assert abertas[0].turma_id in {
            ctx["turma_destino_id"],
            terceira_turma_id,
        }


def test_rollback_se_insercao_da_nova_matricula_falhar(
    client_db,
    contexto_transferencia,
    db,
):
    ctx = contexto_transferencia

    with Session(db) as sessao:
        dados = TransferenciaCriar(
            turma_destino_id=ctx["turma_destino_id"],
            data_transferencia=date(2027, 4, 15),
        )

        # Preserva o método original.
        flush_original = sessao.flush

        def flush_com_falha(*args, **kwargs):
            # Executa o UPDATE e INSERT pendentes
            # dentro da transação, ainda sem commit.
            flush_original(*args, **kwargs)

            # Simula uma falha antes do COMMIT.
            raise RuntimeError(
                "Falha simulada antes do commit"
            )

        with patch.object(
            sessao,
            "flush",
            side_effect=flush_com_falha,
        ):
            with pytest.raises(
                RuntimeError,
                match="Falha simulada",
            ):
                transferir_matricula(
                    matricula_id=ctx["matricula_id"],
                    dados=dados,
                    db=sessao,
                )

        # Garante o encerramento da transação
        # que sofreu a falha.
        sessao.rollback()

    # Uma nova sessão verifica o estado persistido.
    with Session(db) as verificacao:
        matriculas = list(
            verificacao.scalars(
                select(Matricula).where(
                    Matricula.aluno_id == ctx["aluno_id"],
                    Matricula.ano_letivo_id == ctx["ano_id"],
                )
            )
        )

    assert len(matriculas) == 1
    assert matriculas[0].id == ctx["matricula_id"]
    assert matriculas[0].data_fim is None
