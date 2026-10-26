
"""E5.2-B — Testes de integracao de matriculas."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.domain.estados import Perfil
from app.models import Aluno
from tests.api.conftest import login


from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Matricula

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from psycopg import errors
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session




pytestmark = pytest.mark.integration

URL = "/admin/matriculas"
URL_ANOS = "/admin/anos-letivos"
URL_TURMAS = "/admin/turmas"
URL_ALUNOS = "/admin/alunos"


def autenticar_admin(client_db, criar_usuario):
    criar_usuario(perfil=Perfil.ADMIN)

    resposta = login(client_db)
    assert resposta.status_code == 200

    return {
        "X-CSRF-Token": resposta.json()["csrf_token"]
    }


def criar_ano(client_db, headers, ano=2027):
    resposta = client_db.post(
        URL_ANOS,
        json={"ano": ano},
        headers=headers,
    )
    assert resposta.status_code == 201
    return resposta.json()["id"]


def criar_turma(
    client_db,
    headers,
    ano_id,
    identificacao="1 Ano F",
):
    resposta = client_db.post(
        URL_TURMAS,
        json={
            "identificacao": identificacao,
            "ano_escolar": 1,
            "ano_letivo_id": ano_id,
            "turno": "MANHA",
        },
        headers=headers,
    )
    assert resposta.status_code == 201
    return resposta.json()["id"]


def criar_aluno(client_db, headers, matricula="MAT-001"):
    resposta = client_db.post(
        URL_ALUNOS,
        json={
            "nome_completo": "Aluno de Teste",
            "matricula_institucional": matricula,
        },
        headers=headers,
    )
    assert resposta.status_code == 201
    return resposta.json()["id"]


def payload_matricula(
    aluno_id,
    turma_id,
    ano_id,
    inicio="2027-02-01",
    fim=None,
):
    return {
        "aluno_id": aluno_id,
        "turma_id": turma_id,
        "ano_letivo_id": ano_id,
        "data_inicio": inicio,
        "data_fim": fim,
    }


@pytest.fixture
def contexto(client_db, criar_usuario):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)
    turma_id = criar_turma(client_db, headers, ano_id)
    aluno_id = criar_aluno(client_db, headers)

    return {
        "headers": headers,
        "ano_id": ano_id,
        "turma_id": turma_id,
        "aluno_id": aluno_id,
    }


def matricular(client_db, contexto, **alteracoes):
    dados = payload_matricula(
        contexto["aluno_id"],
        contexto["turma_id"],
        contexto["ano_id"],
    )
    dados.update(alteracoes)

    return client_db.post(
        URL,
        json=dados,
        headers=contexto["headers"],
    )


# --------------------------------------------------
# Criacao e periodos
# --------------------------------------------------


def test_admin_cria_matricula(client_db, contexto):
    resposta = matricular(client_db, contexto)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert isinstance(corpo["id"], int)
    assert corpo["aluno_id"] == contexto["aluno_id"]
    assert corpo["turma_id"] == contexto["turma_id"]
    assert corpo["ano_letivo_id"] == contexto["ano_id"]
    assert corpo["data_inicio"] == "2027-02-01"
    assert corpo["data_fim"] is None


@pytest.mark.parametrize(
    "inicio",
    ["2020-02-01", "2035-02-01"],
)
def test_permite_datas_passadas_e_futuras(
    client_db, contexto, inicio
):
    resposta = matricular(
        client_db,
        contexto,
        data_inicio=inicio,
    )

    assert resposta.status_code == 201


def test_permite_matriculas_abertas_em_anos_diferentes(
    client_db, contexto
):
    primeira = matricular(client_db, contexto)
    assert primeira.status_code == 201

    outro_ano = criar_ano(
        client_db,
        contexto["headers"],
        ano=2028,
    )
    outra_turma = criar_turma(
        client_db,
        contexto["headers"],
        outro_ano,
    )

    segunda = matricular(
        client_db,
        contexto,
        ano_letivo_id=outro_ano,
        turma_id=outra_turma,
        data_inicio="2028-02-01",
    )

    assert segunda.status_code == 201


def test_bloqueia_duas_matriculas_abertas_no_mesmo_ano(
    client_db, contexto
):
    primeira = matricular(client_db, contexto)
    assert primeira.status_code == 201

    segunda = matricular(client_db, contexto)

    assert segunda.status_code == 409


def test_bloqueia_periodos_sobrepostos(
    client_db, contexto
):
    primeira = matricular(
        client_db,
        contexto,
        data_fim="2027-04-30",
    )
    assert primeira.status_code == 201

    segunda = matricular(
        client_db,
        contexto,
        data_inicio="2027-04-30",
        data_fim="2027-06-01",
    )

    assert segunda.status_code == 409


def test_permite_periodos_consecutivos(
    client_db, contexto
):
    primeira = matricular(
        client_db,
        contexto,
        data_fim="2027-04-30",
    )
    assert primeira.status_code == 201

    segunda = matricular(
        client_db,
        contexto,
        data_inicio="2027-05-01",
    )

    assert segunda.status_code == 201


def test_rejeita_fim_anterior_ao_inicio(
    client_db, contexto
):
    resposta = matricular(
        client_db,
        contexto,
        data_fim="2027-01-31",
    )

    assert resposta.status_code == 422


# --------------------------------------------------
# Estados cadastrais
# --------------------------------------------------


def test_bloqueia_aluno_inativo(client_db, contexto):
    resposta_patch = client_db.patch(
        f"{URL_ALUNOS}/{contexto['aluno_id']}",
        json={"ativo": False},
        headers=contexto["headers"],
    )
    assert resposta_patch.status_code == 200

    resposta = matricular(client_db, contexto)

    assert resposta.status_code == 409


def test_bloqueia_turma_inativa(client_db, contexto):
    resposta_patch = client_db.patch(
        f"{URL_TURMAS}/{contexto['turma_id']}",
        json={"ativo": False},
        headers=contexto["headers"],
    )
    assert resposta_patch.status_code == 200

    resposta = matricular(client_db, contexto)

    assert resposta.status_code == 409


def test_bloqueia_ano_letivo_inativo(
    client_db, contexto
):
    resposta_patch = client_db.patch(
        f"{URL_ANOS}/{contexto['ano_id']}",
        json={"ativo": False},
        headers=contexto["headers"],
    )
    assert resposta_patch.status_code == 200

    resposta = matricular(client_db, contexto)

    assert resposta.status_code == 409


def test_rejeita_turma_de_outro_ano(
    client_db, contexto
):
    outro_ano = criar_ano(
        client_db,
        contexto["headers"],
        ano=2028,
    )

    resposta = matricular(
        client_db,
        contexto,
        ano_letivo_id=outro_ano,
    )

    assert resposta.status_code == 422


def test_aluno_inexistente_retorna_404(
    client_db, contexto
):
    resposta = matricular(
        client_db,
        contexto,
        aluno_id=999999,
    )

    assert resposta.status_code == 404


def test_turma_inexistente_retorna_404(
    client_db, contexto
):
    resposta = matricular(
        client_db,
        contexto,
        turma_id=999999,
    )

    assert resposta.status_code == 404


def test_ano_inexistente_retorna_404(
    client_db, contexto
):
    resposta = matricular(
        client_db,
        contexto,
        ano_letivo_id=999999,
    )

    assert resposta.status_code == 404


# --------------------------------------------------
# Encerramento e correcao
# --------------------------------------------------


def test_admin_encerra_matricula(client_db, contexto):
    criada = matricular(client_db, contexto)
    assert criada.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{criada.json()['id']}",
        json={"data_fim": "2027-06-30"},
        headers=contexto["headers"],
    )

    assert resposta.status_code == 200
    assert resposta.json()["data_fim"] == "2027-06-30"


def test_admin_corrige_data_de_encerramento(
    client_db, contexto
):
    criada = matricular(
        client_db,
        contexto,
        data_fim="2027-06-30",
    )
    assert criada.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{criada.json()['id']}",
        json={"data_fim": "2027-07-01"},
        headers=contexto["headers"],
    )

    assert resposta.status_code == 200
    assert resposta.json()["data_fim"] == "2027-07-01"


def test_patch_nao_altera_vinculos(
    client_db, contexto
):
    criada = matricular(client_db, contexto)
    assert criada.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{criada.json()['id']}",
        json={"turma_id": 999},
        headers=contexto["headers"],
    )

    assert resposta.status_code == 422


def test_patch_fim_anterior_ao_inicio_retorna_422(
    client_db, contexto
):
    criada = matricular(client_db, contexto)
    assert criada.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{criada.json()['id']}",
        json={"data_fim": "2027-01-01"},
        headers=contexto["headers"],
    )

    assert resposta.status_code == 422


def test_patch_nao_permite_reabrir_matricula(
    client_db, contexto
):
    criada = matricular(
        client_db,
        contexto,
        data_fim="2027-06-30",
    )
    assert criada.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{criada.json()['id']}",
        json={"data_fim": None},
        headers=contexto["headers"],
    )

    assert resposta.status_code == 422


# --------------------------------------------------
# Consultas
# --------------------------------------------------


def test_admin_consulta_matricula(client_db, contexto):
    criada = matricular(client_db, contexto)
    assert criada.status_code == 201

    resposta = client_db.get(
        f"{URL}/{criada.json()['id']}"
    )

    assert resposta.status_code == 200
    assert resposta.json()["id"] == criada.json()["id"]


def test_matricula_inexistente_retorna_404(
    client_db, contexto
):
    resposta = client_db.get(f"{URL}/999999")

    assert resposta.status_code == 404


def test_listagem_filtra_por_aluno(
    client_db, contexto
):
    criada = matricular(client_db, contexto)
    assert criada.status_code == 201

    resposta = client_db.get(
        URL,
        params={"aluno_id": contexto["aluno_id"]},
    )

    assert resposta.status_code == 200
    assert any(
        item["id"] == criada.json()["id"]
        for item in resposta.json()
    )


def test_listagem_filtra_matriculas_abertas(
    client_db, contexto
):
    primeira = matricular(
        client_db,
        contexto,
        data_fim="2027-04-30",
    )
    assert primeira.status_code == 201

    segunda = matricular(
        client_db,
        contexto,
        data_inicio="2027-05-01",
    )
    assert segunda.status_code == 201

    resposta = client_db.get(
        URL,
        params={"aberta": "true"},
    )

    assert resposta.status_code == 200

    ids = {item["id"] for item in resposta.json()}
    assert segunda.json()["id"] in ids
    assert primeira.json()["id"] not in ids


# --------------------------------------------------
# Seguranca e integridade
# --------------------------------------------------


def test_responsavel_nao_cria_matricula(
    client_db, criar_usuario
):
    criar_usuario(perfil=Perfil.RESPONSAVEL)
    autenticacao = login(client_db)
    assert autenticacao.status_code == 200

    resposta = client_db.post(
        URL,
        json={
            "aluno_id": 1,
            "turma_id": 1,
            "ano_letivo_id": 1,
            "data_inicio": "2027-02-01",
        },
        headers={
            "X-CSRF-Token": autenticacao.json()["csrf_token"]
        },
    )

    assert resposta.status_code == 403


def test_sem_autenticacao_retorna_401(client_db):
    resposta = client_db.post(
        URL,
        json={
            "aluno_id": 1,
            "turma_id": 1,
            "ano_letivo_id": 1,
            "data_inicio": "2027-02-01",
        },
    )

    assert resposta.status_code == 401


def test_post_sem_csrf_retorna_403(
    client_db, contexto
):
    resposta = client_db.post(
        URL,
        json=payload_matricula(
            contexto["aluno_id"],
            contexto["turma_id"],
            contexto["ano_id"],
        ),
    )

    assert resposta.status_code == 403


def test_patch_sem_csrf_retorna_403(
    client_db, contexto
):
    criada = matricular(client_db, contexto)
    assert criada.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{criada.json()['id']}",
        json={"data_fim": "2027-06-30"},
    )

    assert resposta.status_code == 403


def test_delete_nao_permitido(client_db, contexto):
    criada = matricular(client_db, contexto)
    assert criada.status_code == 201

    resposta = client_db.delete(
        f"{URL}/{criada.json()['id']}",
        headers=contexto["headers"],
    )

    assert resposta.status_code == 405


def test_sessao_recupera_apos_conflito(
    client_db, contexto
):
    primeira = matricular(client_db, contexto)
    assert primeira.status_code == 201

    duplicada = matricular(client_db, contexto)
    assert duplicada.status_code == 409

    outro_aluno = criar_aluno(
        client_db,
        contexto["headers"],
        matricula="MAT-002",
    )

    valida = matricular(
        client_db,
        contexto,
        aluno_id=outro_aluno,
    )

    assert valida.status_code == 201
    

def test_patch_nao_pode_criar_sobreposicao(
    client_db, contexto
):
    primeira = matricular(
        client_db,
        contexto,
        data_fim="2027-04-30",
    )
    assert primeira.status_code == 201

    segunda = matricular(
        client_db,
        contexto,
        data_inicio="2027-05-01",
        data_fim="2027-06-30",
    )
    assert segunda.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{primeira.json()['id']}",
        json={"data_fim": "2027-05-15"},
        headers=contexto["headers"],
    )

    assert resposta.status_code == 409

    consulta = client_db.get(
        f"{URL}/{primeira.json()['id']}"
    )

    assert consulta.status_code == 200
    assert consulta.json()["data_fim"] == "2027-04-30"


def test_encerramento_preserva_vinculos_originais(
    client_db, contexto
):
    criada = matricular(client_db, contexto)
    assert criada.status_code == 201

    original = criada.json()

    resposta = client_db.patch(
        f"{URL}/{original['id']}",
        json={"data_fim": "2027-06-30"},
        headers=contexto["headers"],
    )

    assert resposta.status_code == 200

    atualizada = resposta.json()

    assert atualizada["id"] == original["id"]
    assert atualizada["aluno_id"] == original["aluno_id"]
    assert atualizada["turma_id"] == original["turma_id"]
    assert (
        atualizada["ano_letivo_id"]
        == original["ano_letivo_id"]
    )
    assert (
        atualizada["data_inicio"]
        == original["data_inicio"]
    )
    assert atualizada["data_fim"] == "2027-06-30"


def test_banco_impede_periodos_sobrepostos(
    client_db, contexto, db
):
    primeira = matricular(
        client_db,
        contexto,
        data_fim="2027-04-30",
    )
    assert primeira.status_code == 201

    conflitante = Matricula(
        aluno_id=contexto["aluno_id"],
        turma_id=contexto["turma_id"],
        ano_letivo_id=contexto["ano_id"],
        data_inicio=date(2027, 4, 15),
        data_fim=date(2027, 5, 30),
    )

    # A fixture db fornece um Engine.
    # Criamos uma Session vinculada a esse Engine.
    with Session(db) as sessao:
        sessao.add(conflitante)

        with pytest.raises(IntegrityError):
            sessao.flush()

        sessao.rollback()
        
def test_banco_impede_matriculas_concorrentes(
    client_db, contexto, db
):
    barreira = Barrier(2, timeout=10)

    
    def inserir(inicio: date, fim: date):
        # Sincronizar as tentativas iniciais.
        barreira.wait()

        for tentativa in range(3):
            try:
                with Session(db) as sessao:
                    matricula = Matricula(
                        aluno_id=contexto["aluno_id"],
                        turma_id=contexto["turma_id"],
                        ano_letivo_id=contexto["ano_id"],
                        data_inicio=inicio,
                        data_fim=fim,
                    )

                    sessao.add(matricula)
                    sessao.commit()

                    return "confirmada"

            except IntegrityError as exc:
                if isinstance(
                    exc.orig,
                    errors.ExclusionViolation,
                ):
                    return "conflito"

                raise

            except OperationalError as exc:
                if not isinstance(
                    exc.orig,
                    errors.DeadlockDetected,
                ):
                    raise

                if tentativa == 2:
                    raise

        raise AssertionError("Tentativas esgotadas.")

    with ThreadPoolExecutor(max_workers=2) as executor:
        primeira = executor.submit(
            inserir,
            date(2027, 2, 1),
            date(2027, 5, 31),
        )
        segunda = executor.submit(
            inserir,
            date(2027, 4, 1),
            date(2027, 7, 31),
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
        matriculas = sessao.query(Matricula).filter(
            Matricula.aluno_id == contexto["aluno_id"],
            Matricula.ano_letivo_id == contexto["ano_id"],
        ).all()

        assert len(matriculas) == 1
