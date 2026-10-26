
"""E5.1-B — Contratos HTTP de turmas (fase RED)."""

import pytest
from sqlalchemy.orm import Session
from datetime import date

from app.models import Aluno, Matricula

from app.domain.estados import Perfil
from app.models import Turma
from tests.api.conftest import login

pytestmark = pytest.mark.integration

URL = "/admin/turmas"
URL_ANOS = "/admin/anos-letivos"

# Ajustar conforme os valores reais do enum Turno.
TURNO_VALIDO = "MANHA"


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


def payload_turma(ano_id, identificacao="1º Ano F"):
    return {
        "identificacao": identificacao,
        "ano_escolar": 1,
        "ano_letivo_id": ano_id,
        "turno": TURNO_VALIDO,
    }


def criar_turma(client_db, headers, ano_id):
    resposta = client_db.post(
        URL,
        json=payload_turma(ano_id),
        headers=headers,
    )
    assert resposta.status_code == 201
    return resposta.json()


# -------------------------------------------------------
# Criacao
# -------------------------------------------------------


def test_admin_cria_turma(client_db, criar_usuario):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)

    resposta = client_db.post(
        URL,
        json=payload_turma(ano_id),
        headers=headers,
    )

    assert resposta.status_code == 201

    corpo = resposta.json()
    assert isinstance(corpo["id"], int)
    assert corpo["identificacao"] == "1º Ano F"
    assert corpo["ano_escolar"] == 1
    assert corpo["ano_letivo_id"] == ano_id
    assert corpo["ativo"] is True


def test_nao_permite_identificacao_duplicada_no_mesmo_ano(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)

    criar_turma(client_db, headers, ano_id)

    resposta = client_db.post(
        URL,
        json=payload_turma(ano_id),
        headers=headers,
    )

    assert resposta.status_code == 409


def test_permite_identificacao_igual_em_anos_diferentes(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    ano_2027 = criar_ano(client_db, headers, 2027)
    ano_2028 = criar_ano(client_db, headers, 2028)

    primeira = client_db.post(
        URL,
        json=payload_turma(ano_2027),
        headers=headers,
    )
    segunda = client_db.post(
        URL,
        json=payload_turma(ano_2028),
        headers=headers,
    )

    assert primeira.status_code == 201
    assert segunda.status_code == 201


def test_nao_cria_turma_em_ano_inexistente(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    resposta = client_db.post(
        URL,
        json=payload_turma(999999),
        headers=headers,
    )

    assert resposta.status_code == 404


def test_nao_cria_turma_em_ano_inativo(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)

    desativacao = client_db.patch(
        f"{URL_ANOS}/{ano_id}",
        json={"ativo": False},
        headers=headers,
    )
    assert desativacao.status_code == 200

    resposta = client_db.post(
        URL,
        json=payload_turma(ano_id),
        headers=headers,
    )

    assert resposta.status_code == 409


# -------------------------------------------------------
# Consulta
# -------------------------------------------------------


def test_admin_lista_turmas(client_db, criar_usuario):
    autenticar_admin(client_db, criar_usuario)

    resposta = client_db.get(URL)

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_admin_consulta_turma_por_id(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)
    turma = criar_turma(client_db, headers, ano_id)

    resposta = client_db.get(f"{URL}/{turma['id']}")

    assert resposta.status_code == 200
    assert resposta.json()["id"] == turma["id"]


def test_turma_inexistente_retorna_404(
    client_db, criar_usuario
):
    autenticar_admin(client_db, criar_usuario)

    resposta = client_db.get(f"{URL}/999999")

    assert resposta.status_code == 404


def test_lista_turmas_filtradas_por_ano(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    ano_2027 = criar_ano(client_db, headers, 2027)
    ano_2028 = criar_ano(client_db, headers, 2028)

    criar_turma(client_db, headers, ano_2027)
    criar_turma(client_db, headers, ano_2028)

    resposta = client_db.get(
        URL,
        params={"ano_letivo_id": ano_2027},
    )

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert resposta.json()[0]["ano_letivo_id"] == ano_2027


# -------------------------------------------------------
# Atualizacao e desativacao
# -------------------------------------------------------


def test_admin_atualiza_identificacao(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)
    turma = criar_turma(client_db, headers, ano_id)

    resposta = client_db.patch(
        f"{URL}/{turma['id']}",
        json={"identificacao": "1º Ano E"},
        headers=headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["identificacao"] == "1º Ano E"


def test_nao_permite_alterar_ano_letivo_da_turma(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    ano_2027 = criar_ano(client_db, headers, 2027)
    ano_2028 = criar_ano(client_db, headers, 2028)

    turma = criar_turma(client_db, headers, ano_2027)

    resposta = client_db.patch(
        f"{URL}/{turma['id']}",
        json={"ano_letivo_id": ano_2028},
        headers=headers,
    )

    assert resposta.status_code == 422


def test_desativar_turma_preserva_registro(
    client_db, criar_usuario, db
):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)
    turma = criar_turma(client_db, headers, ano_id)

    resposta = client_db.patch(
        f"{URL}/{turma['id']}",
        json={"ativo": False},
        headers=headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False

    with Session(db) as session:
        persistida = session.get(Turma, turma["id"])
        assert persistida is not None
        assert persistida.ativo is False
        assert persistida.ano_letivo_id == ano_id


# -------------------------------------------------------
# Autorizacao e validacao
# -------------------------------------------------------


def test_responsavel_nao_cria_turma(
    client_db, criar_usuario
):
    criar_usuario(perfil=Perfil.RESPONSAVEL)
    resposta_login = login(client_db)
    assert resposta_login.status_code == 200

    resposta = client_db.post(
        URL,
        json=payload_turma(1),
        headers={
            "X-CSRF-Token": resposta_login.json()["csrf_token"]
        },
    )

    assert resposta.status_code == 403


def test_sem_autenticacao_nao_lista_turmas(client_db):
    resposta = client_db.get(URL)

    assert resposta.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"identificacao": ""},
        {"ano_escolar": 0},
        {"turno": "INVALIDO"},
    ],
)
def test_payload_invalido_retorna_422(
    client_db, criar_usuario, payload
):
    headers = autenticar_admin(client_db, criar_usuario)

    resposta = client_db.post(
        URL,
        json=payload,
        headers=headers,
    )

    assert resposta.status_code == 422


# -------------------------------------------------------
# E5.1-B — Refactor: integridade e seguranca
# -------------------------------------------------------


def test_desativar_turma_preserva_matricula(
    client_db, criar_usuario, db
):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)
    turma = criar_turma(client_db, headers, ano_id)

    with Session(db) as session:
        aluno = Aluno(
            nome_completo="Aluno de Teste",
            ativo=True,
        )
        session.add(aluno)
        session.flush()

        matricula = Matricula(
            aluno_id=aluno.id,
            turma_id=turma["id"],
            ano_letivo_id=ano_id,
            data_inicio=date(2027, 2, 1),
            data_fim=None,
        )
        session.add(matricula)
        session.flush()
        matricula_id = matricula.id
        aluno_id = aluno.id
        session.commit()

    resposta = client_db.patch(
        f"{URL}/{turma['id']}",
        json={"ativo": False},
        headers=headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False

    with Session(db) as session:
        persistida = session.get(Matricula, matricula_id)
        assert persistida is not None
        assert persistida.aluno_id == aluno_id
        assert persistida.turma_id == turma["id"]
        assert persistida.ano_letivo_id == ano_id
        assert persistida.data_fim is None


def test_filtrar_turmas_ativas_e_inativas(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)

    ativa = criar_turma(client_db, headers, ano_id)

    inativa_resp = client_db.post(
        URL,
        json=payload_turma(ano_id, "1º Ano E"),
        headers=headers,
    )
    assert inativa_resp.status_code == 201
    inativa = inativa_resp.json()

    desativacao = client_db.patch(
        f"{URL}/{inativa['id']}",
        json={"ativo": False},
        headers=headers,
    )
    assert desativacao.status_code == 200

    resposta_ativas = client_db.get(
        URL, params={"ativo": "true"}
    )
    resposta_inativas = client_db.get(
        URL, params={"ativo": "false"}
    )

    assert resposta_ativas.status_code == 200
    assert resposta_inativas.status_code == 200

    assert [t["id"] for t in resposta_ativas.json()] == [
        ativa["id"]
    ]
    assert [t["id"] for t in resposta_inativas.json()] == [
        inativa["id"]
    ]


def test_admin_atualiza_turno(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)
    turma = criar_turma(client_db, headers, ano_id)

    resposta = client_db.patch(
        f"{URL}/{turma['id']}",
        json={"turno": "NOITE"},
        headers=headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["turno"] == "NOITE"


def test_patch_identificacao_duplicada_retorna_409(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)

    primeira = criar_turma(client_db, headers, ano_id)

    segunda_resp = client_db.post(
        URL,
        json=payload_turma(ano_id, "1º Ano E"),
        headers=headers,
    )
    assert segunda_resp.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{segunda_resp.json()['id']}",
        json={"identificacao": primeira["identificacao"]},
        headers=headers,
    )

    assert resposta.status_code == 409


def test_patch_sem_csrf_retorna_403(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)
    turma = criar_turma(client_db, headers, ano_id)

    resposta = client_db.patch(
        f"{URL}/{turma['id']}",
        json={"ativo": False},
    )

    assert resposta.status_code == 403


def test_patch_vazio_retorna_422(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)
    turma = criar_turma(client_db, headers, ano_id)

    resposta = client_db.patch(
        f"{URL}/{turma['id']}",
        json={},
        headers=headers,
    )

    assert resposta.status_code == 422


def test_patch_campo_nulo_retorna_422(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)
    turma = criar_turma(client_db, headers, ano_id)

    resposta = client_db.patch(
        f"{URL}/{turma['id']}",
        json={"identificacao": None},
        headers=headers,
    )

    assert resposta.status_code == 422


def test_sessao_recupera_apos_duplicidade(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers)

    criar_turma(client_db, headers, ano_id)

    duplicada = client_db.post(
        URL,
        json=payload_turma(ano_id),
        headers=headers,
    )
    assert duplicada.status_code == 409

    valida = client_db.post(
        URL,
        json=payload_turma(ano_id, "1º Ano E"),
        headers=headers,
    )

    assert valida.status_code == 201
