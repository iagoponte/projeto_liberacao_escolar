
"""E5.1 — Contratos HTTP de anos letivos (fase RED)."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.estados import Perfil
from app.models import AnoLetivo
from tests.api.conftest import login

pytestmark = pytest.mark.integration

URL = "/admin/anos-letivos"


def autenticar_admin(client_db, criar_usuario):
    criar_usuario(perfil=Perfil.ADMIN)
    resposta = login(client_db)
    assert resposta.status_code == 200
    return {"X-CSRF-Token": resposta.json()["csrf_token"]}


def test_admin_cria_ano_letivo(client_db, criar_usuario):
    headers = autenticar_admin(client_db, criar_usuario)

    resposta = client_db.post(
        URL,
        json={"ano": 2027},
        headers=headers,
    )

    assert resposta.status_code == 201
    assert resposta.json()["ano"] == 2027
    assert resposta.json()["ativo"] is True
    assert isinstance(resposta.json()["id"], int)


def test_nao_permite_ano_letivo_duplicado(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    primeira = client_db.post(
        URL, json={"ano": 2027}, headers=headers
    )
    assert primeira.status_code == 201

    segunda = client_db.post(
        URL, json={"ano": 2027}, headers=headers
    )

    assert segunda.status_code == 409


def test_permite_multiplos_anos_ativos(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    primeiro = client_db.post(
        URL, json={"ano": 2026}, headers=headers
    )
    segundo = client_db.post(
        URL, json={"ano": 2027}, headers=headers
    )

    assert primeiro.status_code == 201
    assert segundo.status_code == 201
    assert primeiro.json()["ativo"] is True
    assert segundo.json()["ativo"] is True


def test_admin_lista_anos_letivos(
    client_db, criar_usuario
):
    autenticar_admin(client_db, criar_usuario)

    resposta = client_db.get(URL)

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_admin_consulta_ano_por_id(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    criado = client_db.post(
        URL, json={"ano": 2027}, headers=headers
    )
    assert criado.status_code == 201

    resposta = client_db.get(f"{URL}/{criado.json()['id']}")

    assert resposta.status_code == 200
    assert resposta.json()["ano"] == 2027


def test_admin_desativa_ano_preservando_registro(
    client_db, criar_usuario, db
):
    headers = autenticar_admin(client_db, criar_usuario)

    criado = client_db.post(
        URL, json={"ano": 2027}, headers=headers
    )
    assert criado.status_code == 201

    ano_id = criado.json()["id"]

    resposta = client_db.patch(
        f"{URL}/{ano_id}",
        json={"ativo": False},
        headers=headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False

    with Session(db) as session:
        ano = session.get(AnoLetivo, ano_id)
        assert ano is not None
        assert ano.ano == 2027
        assert ano.ativo is False


def test_ano_inexistente_retorna_404(
    client_db, criar_usuario
):
    autenticar_admin(client_db, criar_usuario)

    resposta = client_db.get(f"{URL}/999999")

    assert resposta.status_code == 404


def test_responsavel_nao_pode_criar_ano(
    client_db, criar_usuario
):
    criar_usuario(perfil=Perfil.RESPONSAVEL)
    resposta_login = login(client_db)
    assert resposta_login.status_code == 200

    resposta = client_db.post(
        URL,
        json={"ano": 2027},
        headers={
            "X-CSRF-Token": resposta_login.json()["csrf_token"]
        },
    )

    assert resposta.status_code == 403


def test_sem_autenticacao_nao_pode_listar(
    client_db
):
    resposta = client_db.get(URL)

    assert resposta.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"ano": "invalido"},
        {"ano": None},
        {"ano": 2027.5},
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
    

from app.models import Turma
from tests.integration.factories import nova_turma


def test_admin_altera_numero_do_ano(client_db, criar_usuario):
    headers = autenticar_admin(client_db, criar_usuario)

    criado = client_db.post(
        URL, json={"ano": 2027}, headers=headers
    )
    assert criado.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{criado.json()['id']}",
        json={"ano": 2028},
        headers=headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["ano"] == 2028


def test_alterar_ano_preserva_turma_associada(
    client_db, criar_usuario, db
):
    headers = autenticar_admin(client_db, criar_usuario)

    criado = client_db.post(
        URL, json={"ano": 2027}, headers=headers
    )
    assert criado.status_code == 201
    ano_id = criado.json()["id"]

    with Session(db) as session:
        ano = session.get(AnoLetivo, ano_id)
        turma = nova_turma(session, ano_letivo=ano)
        turma_id = turma.id
        session.commit()

    resposta = client_db.patch(
        f"{URL}/{ano_id}",
        json={"ano": 2028},
        headers=headers,
    )

    assert resposta.status_code == 200

    with Session(db) as session:
        turma = session.get(Turma, turma_id)
        assert turma.ano_letivo_id == ano_id
        assert session.get(AnoLetivo, ano_id).ano == 2028


def test_desativar_ano_nao_desativa_turma(
    client_db, criar_usuario, db
):
    headers = autenticar_admin(client_db, criar_usuario)

    criado = client_db.post(
        URL, json={"ano": 2027}, headers=headers
    )
    assert criado.status_code == 201
    ano_id = criado.json()["id"]

    with Session(db) as session:
        turma = nova_turma(
            session,
            ano_letivo=session.get(AnoLetivo, ano_id),
        )
        turma_id = turma.id
        session.commit()

    resposta = client_db.patch(
        f"{URL}/{ano_id}",
        json={"ativo": False},
        headers=headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False

    with Session(db) as session:
        turma = session.get(Turma, turma_id)
        assert turma.ativo is True
        assert turma.ano_letivo_id == ano_id


def test_alterar_ano_para_duplicado_retorna_409(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    primeiro = client_db.post(
        URL, json={"ano": 2027}, headers=headers
    )
    segundo = client_db.post(
        URL, json={"ano": 2028}, headers=headers
    )

    assert primeiro.status_code == 201
    assert segundo.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{segundo.json()['id']}",
        json={"ano": 2027},
        headers=headers,
    )

    assert resposta.status_code == 409


def test_ano_desativado_continua_consultavel(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    criado = client_db.post(
        URL, json={"ano": 2027}, headers=headers
    )
    assert criado.status_code == 201
    ano_id = criado.json()["id"]

    desativado = client_db.patch(
        f"{URL}/{ano_id}",
        json={"ativo": False},
        headers=headers,
    )
    assert desativado.status_code == 200

    resposta = client_db.get(f"{URL}/{ano_id}")

    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False


# -----------------------------------------------------------
# E5.1-A — Refactor: seguranca e consistencia
# -----------------------------------------------------------


def test_post_sem_csrf_retorna_403(client_db, criar_usuario):
    autenticar_admin(client_db, criar_usuario)

    resposta = client_db.post(
        URL,
        json={"ano": 2027},
    )

    assert resposta.status_code == 403


def test_patch_sem_csrf_retorna_403(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    criado = client_db.post(
        URL,
        json={"ano": 2027},
        headers=headers,
    )
    assert criado.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{criado.json()['id']}",
        json={"ativo": False},
    )

    assert resposta.status_code == 403


def test_patch_vazio_retorna_422(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    criado = client_db.post(
        URL,
        json={"ano": 2027},
        headers=headers,
    )
    assert criado.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{criado.json()['id']}",
        json={},
        headers=headers,
    )

    assert resposta.status_code == 422


def test_patch_ativo_nulo_retorna_422(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    criado = client_db.post(
        URL,
        json={"ano": 2027},
        headers=headers,
    )
    assert criado.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{criado.json()['id']}",
        json={"ativo": None},
        headers=headers,
    )

    assert resposta.status_code == 422


def test_patch_atualiza_ano_e_ativo(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    criado = client_db.post(
        URL,
        json={"ano": 2027},
        headers=headers,
    )
    assert criado.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{criado.json()['id']}",
        json={"ano": 2028, "ativo": False},
        headers=headers,
    )

    assert resposta.status_code == 200
    assert resposta.json()["ano"] == 2028
    assert resposta.json()["ativo"] is False


def test_patch_campo_desconhecido_retorna_422(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    criado = client_db.post(
        URL,
        json={"ano": 2027},
        headers=headers,
    )
    assert criado.status_code == 201

    resposta = client_db.patch(
        f"{URL}/{criado.json()['id']}",
        json={"nome": "Ano de teste"},
        headers=headers,
    )

    assert resposta.status_code == 422


def test_sessao_recupera_apos_erro_de_unicidade(
    client_db, criar_usuario
):
    headers = autenticar_admin(client_db, criar_usuario)

    primeiro = client_db.post(
        URL,
        json={"ano": 2027},
        headers=headers,
    )
    assert primeiro.status_code == 201

    duplicado = client_db.post(
        URL,
        json={"ano": 2027},
        headers=headers,
    )
    assert duplicado.status_code == 409

    novo = client_db.post(
        URL,
        json={"ano": 2028},
        headers=headers,
    )

    assert novo.status_code == 201
    assert novo.json()["ano"] == 2028
