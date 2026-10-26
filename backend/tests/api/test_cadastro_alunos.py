
"""E5.2-A — Contratos HTTP do cadastro administrativo de alunos."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.domain.estados import Perfil
from app.models import Aluno, Matricula
from tests.api.conftest import login

pytestmark = pytest.mark.integration

URL = "/admin/alunos"
URL_ANOS = "/admin/anos-letivos"
URL_TURMAS = "/admin/turmas"


def autenticar_admin(client_db, criar_usuario):
    criar_usuario(perfil=Perfil.ADMIN)
    resposta = login(client_db)
    assert resposta.status_code == 200
    return {"X-CSRF-Token": resposta.json()["csrf_token"]}


def criar_aluno(
    client_db,
    headers,
    nome="Maria Oliveira",
    matricula="MAT-001",
):
    resposta = client_db.post(
        URL,
        json={
            "nome_completo": nome,
            "matricula_institucional": matricula,
        },
        headers=headers,
    )
    assert resposta.status_code == 201
    return resposta.json()


# -------------------------------------------------------
# Cadastro
# -------------------------------------------------------


def test_admin_cadastra_aluno(client_db, criar_usuario):
    headers = autenticar_admin(client_db, criar_usuario)

    resposta = client_db.post(
        URL,
        json={
            "nome_completo": "Maria Oliveira",
            "matricula_institucional": "MAT-001",
        },
        headers=headers,
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert isinstance(corpo["id"], int)
    assert corpo["nome_completo"] == "Maria Oliveira"
    assert corpo["matricula_institucional"] == "MAT-001"
    assert corpo["ativo"] is True


def test_cadastra_aluno_sem_matricula_institucional(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    resposta = client_db.post(
        URL,
        json={"nome_completo": "Joao Silva"},
        headers=headers,
    )

    assert resposta.status_code == 201
    assert resposta.json()["matricula_institucional"] is None


def test_permite_alunos_com_nomes_iguais(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    primeiro = criar_aluno(
        client_db, headers, "Maria Oliveira", "MAT-001"
    )
    segundo = criar_aluno(
        client_db, headers, "Maria Oliveira", "MAT-002"
    )

    assert primeiro["id"] != segundo["id"]


def test_matricula_institucional_duplicada_retorna_409(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    criar_aluno(client_db, headers)

    resposta = client_db.post(
        URL,
        json={
            "nome_completo": "Outro Aluno",
            "matricula_institucional": "MAT-001",
        },
        headers=headers,
    )

    assert resposta.status_code == 409


# -------------------------------------------------------
# Consulta
# -------------------------------------------------------


def test_admin_consulta_aluno_por_id(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    aluno = criar_aluno(client_db, headers)

    resposta = client_db.get(f"{URL}/{aluno['id']}")

    assert resposta.status_code == 200
    assert resposta.json()["id"] == aluno["id"]


def test_aluno_inexistente_retorna_404(
    client_db, criar_usuario
):
    autenticar_admin(client_db, criar_usuario)

    resposta = client_db.get(f"{URL}/999999")

    assert resposta.status_code == 404


def test_listagem_admin_inclui_aluno_cadastrado(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    aluno = criar_aluno(client_db, headers)

    resposta = client_db.get(URL)

    assert resposta.status_code == 200
    assert any(
        item["id"] == aluno["id"]
        for item in resposta.json()
    )


# -------------------------------------------------------
# Atualizacao
# -------------------------------------------------------


def test_admin_corrige_nome(client_db, criar_usuario):
    headers = autenticar_admin(client_db, criar_usuario)
    aluno = criar_aluno(client_db, headers)

    resposta = client_db.patch(
        f"{URL}/{aluno['id']}",
        json={"nome_completo": "Maria de Oliveira"},
        headers=headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["nome_completo"] == "Maria de Oliveira"


def test_admin_altera_matricula_institucional(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    aluno = criar_aluno(client_db, headers)

    resposta = client_db.patch(
        f"{URL}/{aluno['id']}",
        json={"matricula_institucional": "MAT-002"},
        headers=headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["matricula_institucional"] == "MAT-002"


def test_admin_atribui_matricula_antes_ausente(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    aluno = criar_aluno(client_db, headers, matricula=None)

    resposta = client_db.patch(
        f"{URL}/{aluno['id']}",
        json={"matricula_institucional": "MAT-003"},
        headers=headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["matricula_institucional"] == "MAT-003"


def test_admin_remove_matricula_institucional(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    aluno = criar_aluno(client_db, headers)

    resposta = client_db.patch(
        f"{URL}/{aluno['id']}",
        json={"matricula_institucional": None},
        headers=headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["matricula_institucional"] is None


def test_patch_matricula_duplicada_retorna_409(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    criar_aluno(client_db, headers)

    segundo = criar_aluno(
        client_db, headers, "Joao Silva", "MAT-002"
    )

    resposta = client_db.patch(
        f"{URL}/{segundo['id']}",
        json={"matricula_institucional": "MAT-001"},
        headers=headers,
    )

    assert resposta.status_code == 409


# -------------------------------------------------------
# Desativacao e reativacao
# -------------------------------------------------------


def test_admin_desativa_aluno_preservando_registro(
    client_db, criar_usuario, db
):
    headers = autenticar_admin(client_db, criar_usuario)
    aluno = criar_aluno(client_db, headers)

    resposta = client_db.patch(
        f"{URL}/{aluno['id']}",
        json={"ativo": False},
        headers=headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False

    with Session(db) as session:
        persistido = session.get(Aluno, aluno["id"])
        assert persistido is not None
        assert persistido.ativo is False


def test_admin_reativa_aluno(client_db, criar_usuario):
    headers = autenticar_admin(client_db, criar_usuario)
    aluno = criar_aluno(client_db, headers)

    desativacao = client_db.patch(
        f"{URL}/{aluno['id']}",
        json={"ativo": False},
        headers=headers,
    )
    assert desativacao.status_code == 200

    resposta = client_db.patch(
        f"{URL}/{aluno['id']}",
        json={"ativo": True},
        headers=headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is True


def test_desativacao_preserva_matricula_aberta(
    client_db, criar_usuario, db
):
    headers = autenticar_admin(client_db, criar_usuario)
    aluno = criar_aluno(client_db, headers)

    ano_resp = client_db.post(
        URL_ANOS,
        json={"ano": 2027},
        headers=headers,
    )
    assert ano_resp.status_code == 201
    ano_id = ano_resp.json()["id"]

    turma_resp = client_db.post(
        URL_TURMAS,
        json={
            "identificacao": "1 Ano F",
            "ano_escolar": 1,
            "ano_letivo_id": ano_id,
            "turno": "MANHA",
        },
        headers=headers,
    )
    assert turma_resp.status_code == 201
    turma_id = turma_resp.json()["id"]

    with Session(db) as session:
        matricula = Matricula(
            aluno_id=aluno["id"],
            turma_id=turma_id,
            ano_letivo_id=ano_id,
            data_inicio=date(2027, 2, 1),
            data_fim=None,
        )
        session.add(matricula)
        session.flush()
        matricula_id = matricula.id
        session.commit()

    resposta = client_db.patch(
        f"{URL}/{aluno['id']}",
        json={"ativo": False},
        headers=headers,
    )

    assert resposta.status_code == 200

    with Session(db) as session:
        persistida = session.get(Matricula, matricula_id)
        assert persistida is not None
        assert persistida.aluno_id == aluno["id"]
        assert persistida.turma_id == turma_id
        assert persistida.data_fim is None


# -------------------------------------------------------
# Autorizacao e CSRF
# -------------------------------------------------------


def test_responsavel_nao_cadastra_aluno(
    client_db, criar_usuario
):
    criar_usuario(perfil=Perfil.RESPONSAVEL)
    resposta_login = login(client_db)
    assert resposta_login.status_code == 200

    resposta = client_db.post(
        URL,
        json={"nome_completo": "Aluno Teste"},
        headers={
            "X-CSRF-Token": resposta_login.json()["csrf_token"]
        },
    )

    assert resposta.status_code == 403


def test_sem_autenticacao_nao_cadastra_aluno(client_db):
    resposta = client_db.post(
        URL,
        json={"nome_completo": "Aluno Teste"},
    )

    assert resposta.status_code == 401


def test_post_sem_csrf_retorna_403(
    client_db, criar_usuario
):
    autenticar_admin(client_db, criar_usuario)

    resposta = client_db.post(
        URL,
        json={"nome_completo": "Aluno Teste"},
    )

    assert resposta.status_code == 403


def test_patch_sem_csrf_retorna_403(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    aluno = criar_aluno(client_db, headers)

    resposta = client_db.patch(
        f"{URL}/{aluno['id']}",
        json={"ativo": False},
    )

    assert resposta.status_code == 403


# -------------------------------------------------------
# Validacao
# -------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"nome_completo": ""},
        {"nome_completo": None},
        {"nome_completo": 123},
    ],
)
def test_cadastro_invalido_retorna_422(
    client_db, criar_usuario, payload
):
    headers = autenticar_admin(client_db, criar_usuario)

    resposta = client_db.post(
        URL,
        json=payload,
        headers=headers,
    )

    assert resposta.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"nome_completo": None},
        {"ativo": None},
        {"campo_desconhecido": "valor"},
    ],
)
def test_patch_invalido_retorna_422(
    client_db, criar_usuario, payload
):
    headers = autenticar_admin(client_db, criar_usuario)
    aluno = criar_aluno(client_db, headers)

    resposta = client_db.patch(
        f"{URL}/{aluno['id']}",
        json=payload,
        headers=headers,
    )

    assert resposta.status_code == 422


def test_sessao_recupera_apos_duplicidade(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    criar_aluno(client_db, headers)

    duplicado = client_db.post(
        URL,
        json={
            "nome_completo": "Outro Aluno",
            "matricula_institucional": "MAT-001",
        },
        headers=headers,
    )
    assert duplicado.status_code == 409

    valido = client_db.post(
        URL,
        json={
            "nome_completo": "Novo Aluno",
            "matricula_institucional": "MAT-003",
        },
        headers=headers,
    )

    assert valido.status_code == 201


@pytest.mark.parametrize(
    "nome",
    [" ", "   ", "\t", "\n"],
)
def test_rejeita_nome_apenas_com_espacos(
    client_db, criar_usuario, nome
):
    headers = autenticar_admin(client_db, criar_usuario)

    resposta = client_db.post(
        URL,
        json={"nome_completo": nome},
        headers=headers,
    )

    assert resposta.status_code == 422


def test_normaliza_espacos_do_nome(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    resposta = client_db.post(
        URL,
        json={"nome_completo": "  Maria Oliveira  "},
        headers=headers,
    )

    assert resposta.status_code == 201
    assert resposta.json()["nome_completo"] == "Maria Oliveira"


def test_normaliza_matricula_institucional(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    resposta = client_db.post(
        URL,
        json={
            "nome_completo": "Maria Oliveira",
            "matricula_institucional": "  MAT-001  ",
        },
        headers=headers,
    )

    assert resposta.status_code == 201
    assert resposta.json()["matricula_institucional"] == "MAT-001"


def test_patch_nome_apenas_espacos_retorna_422(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)
    aluno = criar_aluno(client_db, headers)

    resposta = client_db.patch(
        f"{URL}/{aluno['id']}",
        json={"nome_completo": "   "},
        headers=headers,
    )

    assert resposta.status_code == 422


def test_patch_aluno_inexistente_retorna_404(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    resposta = client_db.patch(
        f"{URL}/999999",
        json={"nome_completo": "Novo Nome"},
        headers=headers,
    )

    assert resposta.status_code == 404


def test_matricula_vazia_e_normalizada_para_null(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    resposta = client_db.post(
        URL,
        json={
            "nome_completo": "Maria Oliveira",
            "matricula_institucional": "   ",
        },
        headers=headers,
    )

    assert resposta.status_code == 201
    assert resposta.json()["matricula_institucional"] is None
