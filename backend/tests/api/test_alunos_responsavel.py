
"""E5.3-C — Consulta dos alunos do responsável autenticado."""

import pytest

from app.domain.estados import Perfil
from tests.api.conftest import login
from tests.api.test_matriculas import autenticar_admin, criar_aluno
from tests.api.test_vinculos import criar_vinculo

pytestmark = pytest.mark.integration

URL = "/responsavel/alunos"


def test_responsavel_consulta_seus_alunos(
    client_db,
    criar_usuario,
    criar_responsavel,
):
    # Arrange: cadastrar responsável e aluno.
    responsavel_id = criar_responsavel()
    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="RESP-001",
    )

    resposta_vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert resposta_vinculo.status_code == 201

    # Autenticar como responsável.
    resposta_login = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert resposta_login.status_code == 200

    # Act
    resposta = client_db.get(URL)

    # Assert
    assert resposta.status_code == 200

    alunos = resposta.json()

    assert isinstance(alunos, list)
    assert len(alunos) == 1
    assert alunos[0]["id"] == aluno_id


def test_responsavel_nao_visualiza_aluno_de_outro_responsavel(
    client_db,
    criar_usuario,
    criar_responsavel,
):
    # ARRANGE — criar dois responsáveis diferentes
    responsavel_1_id = criar_responsavel()
    responsavel_2_id = criar_responsavel()

    # Autenticar administrador
    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    # Criar dois alunos distintos
    aluno_1_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="ISOL-001",
    )

    aluno_2_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="ISOL-002",
    )

    # Vincular cada responsável ao seu aluno
    vinculo_1 = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_1_id,
        aluno_1_id,
    )

    vinculo_2 = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_2_id,
        aluno_2_id,
    )

    assert vinculo_1.status_code == 201
    assert vinculo_2.status_code == 201

    # Autenticar somente o primeiro responsável
    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )

    assert autenticacao.status_code == 200

    # ACT — consultar os alunos do responsável autenticado
    resposta = client_db.get("/responsavel/alunos")

    # ASSERT — o responsável acessa apenas seu próprio aluno
    assert resposta.status_code == 200

    alunos = resposta.json()
    ids_retornados = {aluno["id"] for aluno in alunos}

    assert ids_retornados == {aluno_1_id}
    assert aluno_2_id not in ids_retornados


def test_responsavel_nao_visualiza_aluno_com_vinculo_revogado(
    client_db,
    criar_usuario,
    criar_responsavel,
    relogio,
):
    # ARRANGE — criar responsável
    responsavel_id = criar_responsavel()

    # Autenticar administrador
    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    # Criar aluno
    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="REV-001",
    )

    # Criar vínculo ativo
    criado = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert criado.status_code == 201

    vinculo_id = criado.json()["id"]

    # Autenticar como responsável
    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    # Antes da revogação: aluno deve estar visível
    antes = client_db.get("/responsavel/alunos")

    assert antes.status_code == 200
    assert aluno_id in {
        aluno["id"] for aluno in antes.json()
    }

    # Avançar o relógio para respeitar a vigência
    relogio.avancar(seconds=1)

    # Reautenticar como administrador
    login_admin = login(
        client_db,
        email="pessoa@exemplo.test",
    )
    assert login_admin.status_code == 200

    headers_admin = {
        "X-CSRF-Token": login_admin.json()["csrf_token"]
    }

    # Revogar o vínculo
    revogado = client_db.post(
        f"/admin/vinculos/{vinculo_id}/revogar",
        headers=headers_admin,
    )

    assert revogado.status_code == 200
    assert revogado.json()["ativo"] is False

    # Reautenticar como responsável
    novo_login = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert novo_login.status_code == 200

    # ACT — consultar os alunos depois da revogação
    depois = client_db.get("/responsavel/alunos")

    # ASSERT — vínculo revogado não concede mais acesso
    assert depois.status_code == 200
    assert depois.json() == []
    

def test_responsavel_nao_visualiza_aluno_inativo(
    client_db,
    criar_usuario,
    criar_responsavel,
):
    # ARRANGE — cadastrar responsável
    responsavel_id = criar_responsavel()

    # Autenticar administrador
    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    # Cadastrar aluno
    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="INAT-001",
    )

    # Criar vínculo ativo entre responsável e aluno
    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )
    assert vinculo.status_code == 201

    # Desativar o aluno mantendo o vínculo existente
    alteracao = client_db.patch(
        f"/admin/alunos/{aluno_id}",
        json={"ativo": False},
        headers=headers_admin,
    )
    assert alteracao.status_code == 200

    # Autenticar como responsável
    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    # ACT — consultar alunos vinculados
    resposta = client_db.get("/responsavel/alunos")

    # ASSERT — aluno inativo não deve aparecer
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_responsavel_sem_vinculos_recebe_lista_vazia(
    client_db,
    criar_responsavel,
):
    # ARRANGE — cadastrar responsável sem vincular alunos
    responsavel_id = criar_responsavel()

    assert isinstance(responsavel_id, int)

    # Autenticar como responsável
    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )

    assert autenticacao.status_code == 200

    # ACT — consultar alunos vinculados
    resposta = client_db.get("/responsavel/alunos")

    # ASSERT — consulta válida, sem alunos
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_usuario_nao_autenticado_nao_consulta_alunos(
    client_db,
):
    # ARRANGE — garantir ausência do cookie de sessão
    client_db.cookies.clear()

    # ACT — tentar consultar sem autenticação
    resposta = client_db.get("/responsavel/alunos")

    # ASSERT — acesso negado
    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "Nao autenticado."


def test_admin_nao_pode_consultar_alunos_como_responsavel(
    client_db,
    criar_usuario,
):
    # ARRANGE — criar e autenticar administrador
    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    assert "X-CSRF-Token" in headers_admin

    # ACT — administrador tenta acessar endpoint
    # exclusivo dos responsáveis
    resposta = client_db.get("/responsavel/alunos")

    # ASSERT — usuário autenticado, mas sem autorização
    assert resposta.status_code == 403
    assert resposta.json()["detail"] == (
        "Acesso restrito a responsaveis."
    )


def test_responsavel_nao_consulta_diretamente_aluno_de_outro(
    client_db,
    criar_usuario,
    criar_responsavel,
):
    # ARRANGE — cadastrar dois responsáveis
    responsavel_1_id = criar_responsavel()
    responsavel_2_id = criar_responsavel()

    # Autenticar administrador
    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    # Criar dois alunos
    aluno_1_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="IDOR-001",
    )

    aluno_2_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="IDOR-002",
    )

    # Criar vínculos separados
    vinculo_1 = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_1_id,
        aluno_1_id,
    )

    vinculo_2 = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_2_id,
        aluno_2_id,
    )

    assert vinculo_1.status_code == 201
    assert vinculo_2.status_code == 201

    # Autenticar como Responsável 1
    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )

    assert autenticacao.status_code == 200

    # Controle positivo: deve acessar o próprio aluno
    permitido = client_db.get(
        f"/responsavel/alunos/{aluno_1_id}"
    )

    assert permitido.status_code == 200
    assert permitido.json()["id"] == aluno_1_id

    # ACT — tentar acessar diretamente o aluno de outro
    resposta = client_db.get(
        f"/responsavel/alunos/{aluno_2_id}"
    )

    # ASSERT — acesso não autorizado não revela o aluno
    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Aluno nao encontrado."


def test_responsavel_com_cadastro_inativo_nao_visualiza_alunos(
    client_db,
    criar_usuario,
    criar_responsavel,
    db,
):
    from sqlalchemy.orm import Session
    from app.models import Responsavel

    # ARRANGE — criar responsável ativo
    responsavel_id = criar_responsavel()

    # Autenticar administrador
    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    # Cadastrar aluno
    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="RESP-INAT-001",
    )

    # Criar vínculo enquanto o responsável está ativo
    vinculo = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )

    assert vinculo.status_code == 201

    # Desativar somente o cadastro do responsável.
    # A conta Usuario permanece ativa.
    with Session(db) as sessao:
        responsavel = sessao.get(
            Responsavel,
            responsavel_id,
        )

        assert responsavel is not None
        responsavel.ativo = False
        sessao.commit()

    # Autenticar com a conta do responsável
    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )

    assert autenticacao.status_code == 200

    # ACT — consultar os alunos vinculados
    resposta = client_db.get("/responsavel/alunos")

    # ASSERT — cadastro inativo não concede acesso
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_responsavel_nao_consulta_aluno_apos_revogacao(
    client_db,
    criar_usuario,
    criar_responsavel,
    relogio,
):
    # ARRANGE — criar responsável e autenticar administrador
    responsavel_id = criar_responsavel()

    headers_admin = autenticar_admin(
        client_db,
        criar_usuario,
    )

    aluno_id = criar_aluno(
        client_db,
        headers_admin,
        matricula="REV-DIRETO-001",
    )

    criado = criar_vinculo(
        client_db,
        headers_admin,
        responsavel_id,
        aluno_id,
    )

    assert criado.status_code == 201
    vinculo_id = criado.json()["id"]

    # Autenticar como responsável
    autenticacao = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert autenticacao.status_code == 200

    # Controle positivo: acesso permitido antes da revogação
    antes = client_db.get(
        f"/responsavel/alunos/{aluno_id}"
    )

    assert antes.status_code == 200
    assert antes.json()["id"] == aluno_id

    # Avançar o relógio antes de revogar
    relogio.avancar(seconds=1)

    # Reautenticar como administrador
    login_admin = login(
        client_db,
        email="pessoa@exemplo.test",
    )
    assert login_admin.status_code == 200

    headers_admin = {
        "X-CSRF-Token": login_admin.json()["csrf_token"]
    }

    revogado = client_db.post(
        f"/admin/vinculos/{vinculo_id}/revogar",
        headers=headers_admin,
    )

    assert revogado.status_code == 200

    # Reautenticar como responsável
    novo_login = login(
        client_db,
        email="responsavel1@exemplo.test",
    )
    assert novo_login.status_code == 200

    # ACT — tentar consultar diretamente o aluno revogado
    depois = client_db.get(
        f"/responsavel/alunos/{aluno_id}"
    )

    # ASSERT — vínculo revogado não permite acesso
    assert depois.status_code == 404
    assert depois.json()["detail"] == "Aluno nao encontrado."
