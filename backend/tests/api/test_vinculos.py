
"""E5.3 — RED inicial dos vínculos responsável-aluno."""

import pytest

from app.domain.estados import Perfil
from tests.api.conftest import login
from tests.api.test_matriculas import (
    autenticar_admin,
    criar_aluno,
)
from sqlalchemy.orm import Session
from app.models import Responsavel, Aluno

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
from sqlalchemy import select
from app.models import ResponsavelAluno

pytestmark = pytest.mark.integration

URL_VINCULOS = "/admin/vinculos"
URL_ALUNOS = "/admin/alunos"


@pytest.fixture
def contexto_vinculo(client_db, criar_usuario):
    headers = autenticar_admin(client_db, criar_usuario)

    aluno_id = criar_aluno(
        client_db,
        headers,
        matricula="VINC-001",
    )

    return {
        "headers": headers,
        "aluno_id": aluno_id,
    }


def criar_vinculo(
    client_db,
    headers,
    responsavel_id,
    aluno_id,
):
    return client_db.post(
        URL_VINCULOS,
        json={
            "responsavel_id": responsavel_id,
            "aluno_id": aluno_id,
        },
        headers=headers,
    )


def test_admin_cria_vinculo_valido(
    client_db,
    contexto_vinculo,
    criar_responsavel,
):
    ctx = contexto_vinculo

    responsavel_id = criar_responsavel()

    resposta = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        ctx["aluno_id"],
    )

    assert resposta.status_code == 201

    dados = resposta.json()

    assert isinstance(dados["id"], int)
    assert dados["responsavel_id"] == responsavel_id
    assert dados["aluno_id"] == ctx["aluno_id"]
    assert dados["ativo"] is True


def test_admin_consulta_vinculo(
    client_db,
    contexto_vinculo,
    criar_responsavel,
):
    ctx = contexto_vinculo

    responsavel_id = criar_responsavel()

    criacao = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        ctx["aluno_id"],
    )

    assert criacao.status_code == 201

    vinculo_id = criacao.json()["id"]

    consulta = client_db.get(
        f"{URL_VINCULOS}/{vinculo_id}",
    )

    assert consulta.status_code == 200
    assert consulta.json()["id"] == vinculo_id
    assert consulta.json()["aluno_id"] == ctx["aluno_id"]


def test_responsavel_pode_ter_varios_alunos(
    client_db,
    contexto_vinculo,
    criar_responsavel,
):
    ctx = contexto_vinculo

    responsavel_id = criar_responsavel()

    outro_aluno_id = criar_aluno(
        client_db,
        ctx["headers"],
        matricula="VINC-002",
    )

    primeira = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        ctx["aluno_id"],
    )

    segunda = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        outro_aluno_id,
    )

    assert primeira.status_code == 201
    assert segunda.status_code == 201

    assert primeira.json()["id"] != segunda.json()["id"]


def test_aluno_pode_ter_varios_responsaveis(
    client_db,
    contexto_vinculo,
    criar_responsavel,
):
    ctx = contexto_vinculo

    primeiro_responsavel_id = criar_responsavel()

    segundo_responsavel_id = criar_responsavel()

    primeira = criar_vinculo(
        client_db,
        ctx["headers"],
        primeiro_responsavel_id,
        ctx["aluno_id"],
    )

    segunda = criar_vinculo(
        client_db,
        ctx["headers"],
        segundo_responsavel_id,
        ctx["aluno_id"],
    )

    assert primeira.status_code == 201
    assert segunda.status_code == 201


def test_nao_permite_vinculo_duplicado(
    client_db,
    contexto_vinculo,
    criar_responsavel,
):
    ctx = contexto_vinculo

    responsavel_id = criar_responsavel()

    primeira = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        ctx["aluno_id"],
    )

    assert primeira.status_code == 201

    segunda = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        ctx["aluno_id"],
    )

    assert segunda.status_code == 409


def test_nao_vincula_aluno_inativo(
    client_db,
    contexto_vinculo,
    criar_responsavel,
):
    ctx = contexto_vinculo

    responsavel_id = criar_responsavel()

    alteracao = client_db.patch(
        f"{URL_ALUNOS}/{ctx['aluno_id']}",
        json={"ativo": False},
        headers=ctx["headers"],
    )

    assert alteracao.status_code == 200

    resposta = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        ctx["aluno_id"],
    )

    assert resposta.status_code == 409


def test_nao_vincula_aluno_inexistente(
    client_db,
    contexto_vinculo,
    criar_responsavel,
):
    ctx = contexto_vinculo

    responsavel_id = criar_responsavel()

    resposta = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        999999,
    )

    assert resposta.status_code == 404



def test_nao_vincula_usuario_admin(
    client_db,
    contexto_vinculo,
    criar_usuario,
    db,
):
    ctx = contexto_vinculo

    usuario_admin_id = criar_usuario(
        email="admin-vinculos@exemplo.test",
        perfil=Perfil.ADMIN,
    )

    with Session(db) as sessao:
        responsavel = Responsavel(
            usuario_id=usuario_admin_id,
            nome_completo="Responsavel com perfil invalido",
            ativo=True,
        )

        sessao.add(responsavel)
        sessao.commit()
        responsavel_id = responsavel.id

    resposta = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        ctx["aluno_id"],
    )

    assert resposta.status_code == 409



# @pytest.fixture
# def criar_responsavel(db, criar_usuario):
#     contador = 0

#     def _criar(ativo=True):
#         nonlocal contador
#         contador += 1

#         usuario_id = criar_usuario(
#             email=f"responsavel{contador}@exemplo.test",
#             perfil=Perfil.RESPONSAVEL,
#             ativo=ativo,
#         )

#         with Session(db) as sessao:
#             responsavel = Responsavel(
#                 usuario_id=usuario_id,
#                 nome_completo=f"Responsavel {contador}",
#                 ativo=ativo,
#             )

#             sessao.add(responsavel)
#             sessao.commit()
#             return responsavel.id

#     return _criar

def test_admin_revoga_vinculo_ativo(
    client_db,
    contexto_vinculo,
    criar_responsavel,
    relogio,
):
    ctx = contexto_vinculo
    responsavel_id = criar_responsavel()
    
    criado = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        ctx["aluno_id"],
    )
    assert criado.status_code == 201
    vinculo_id = criado.json()["id"]
    
    relogio.avancar(seconds=1)
    
    resposta = client_db.post(
        f"/admin/vinculos/{vinculo_id}/revogar",
        headers=ctx["headers"],
    )

    assert resposta.status_code == 200
    assert resposta.json()["id"] == vinculo_id
    assert resposta.json()["ativo"] is False
    assert resposta.json()["revogado_em"] is not None

    consulta = client_db.get(
        f"/admin/vinculos/{vinculo_id}",
    )
    assert consulta.status_code == 200
    assert consulta.json()["ativo"] is False


def test_admin_nao_revoga_vinculo_duas_vezes(
    client_db,
    contexto_vinculo,
    criar_responsavel,
    relogio,
):
    ctx = contexto_vinculo
    responsavel_id = criar_responsavel()

    criado = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        ctx["aluno_id"],
    )
    vinculo_id = criado.json()["id"]
    
    relogio.avancar(seconds=1)

    url = f"/admin/vinculos/{vinculo_id}/revogar"

    primeira = client_db.post(url, headers=ctx["headers"])
    segunda = client_db.post(url, headers=ctx["headers"])

    assert primeira.status_code == 200
    assert segunda.status_code == 409


def test_admin_nao_revoga_vinculo_inexistente(
    client_db,
    contexto_vinculo,
):
    resposta = client_db.post(
        "/admin/vinculos/999999/revogar",
        headers=contexto_vinculo["headers"],
    )

    assert resposta.status_code == 404


def test_admin_reativa_vinculo_preservando_historico(
    client_db,
    contexto_vinculo,
    criar_responsavel,
    relogio,
):
    ctx = contexto_vinculo
    responsavel_id = criar_responsavel()

    criado = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        ctx["aluno_id"],
    )
    assert criado.status_code == 201
    vinculo_original_id = criado.json()["id"]
    
    relogio.avancar(seconds=1)

    revogado = client_db.post(
        f"/admin/vinculos/{vinculo_original_id}/revogar",
        headers=ctx["headers"],
    )
    assert revogado.status_code == 200

    relogio.avancar(seconds=1)
    
    resposta = client_db.post(
        f"/admin/vinculos/{vinculo_original_id}/reativar",
        headers=ctx["headers"],
    )

    assert resposta.status_code == 201

    novo = resposta.json()

    assert novo["id"] != vinculo_original_id
    assert novo["responsavel_id"] == responsavel_id
    assert novo["aluno_id"] == ctx["aluno_id"]
    assert novo["ativo"] is True

    historico = client_db.get(
        f"/admin/vinculos/{vinculo_original_id}",
    )
    assert historico.status_code == 200
    assert historico.json()["ativo"] is False


def test_admin_nao_reativa_vinculo_ainda_ativo(
    client_db,
    contexto_vinculo,
    criar_responsavel,
):
    ctx = contexto_vinculo
    responsavel_id = criar_responsavel()

    criado = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        ctx["aluno_id"],
    )
    vinculo_id = criado.json()["id"]

    resposta = client_db.post(
        f"/admin/vinculos/{vinculo_id}/reativar",
        headers=ctx["headers"],
    )

    assert resposta.status_code == 409


def test_admin_nao_reativa_vinculo_com_aluno_inativo(
    client_db,
    contexto_vinculo,
    criar_responsavel,
    db,
    relogio,
):
    ctx = contexto_vinculo
    responsavel_id = criar_responsavel()

    criado = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        ctx["aluno_id"],
    )
    vinculo_id = criado.json()["id"]
    
    relogio.avancar(seconds=1)

    revogado = client_db.post(
        f"/admin/vinculos/{vinculo_id}/revogar",
        headers=ctx["headers"],
    )
    assert revogado.status_code == 200

    with Session(db) as sessao:
        aluno = sessao.get(Aluno, ctx["aluno_id"])
        aluno.ativo = False
        sessao.commit()

    resposta = client_db.post(
        f"/admin/vinculos/{vinculo_id}/reativar",
        headers=ctx["headers"],
    )

    assert resposta.status_code == 409


def test_duas_reativacoes_simultaneas_nao_criam_vinculos_duplicados(
    client_db,
    contexto_vinculo,
    criar_responsavel,
    criar_usuario,
    db,
    relogio,
):
    ctx = contexto_vinculo

    responsavel_id = criar_responsavel()

    criado = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        ctx["aluno_id"],
    )
    assert criado.status_code == 201

    vinculo_original_id = criado.json()["id"]

    # A revogação precisa acontecer depois da criação.
    relogio.avancar(seconds=1)

    revogado = client_db.post(
        f"/admin/vinculos/{vinculo_original_id}/revogar",
        headers=ctx["headers"],
    )
    assert revogado.status_code == 200

    # A reativação será posterior à revogação.
    relogio.avancar(seconds=1)

    # Utilizar a aplicação já existente.
    from app.main import app

    # Criar duas sessões administrativas distintas.
    # Os usuários terão emails exclusivos.
    criar_usuario(
        email="admin-concorrente-a@exemplo.test",
        perfil=Perfil.ADMIN,
    )

    criar_usuario(
        email="admin-concorrente-b@exemplo.test",
        perfil=Perfil.ADMIN,
    )

    barreira = Barrier(2, timeout=10)

    def reativar(email):
        with TestClient(app) as cliente:
            autenticacao = login(
                cliente,
                email=email,
            )

            assert autenticacao.status_code == 200

            headers = {
                "X-CSRF-Token": autenticacao.json()["csrf_token"]
            }

            # As duas requisições começam juntas.
            barreira.wait()

            resposta = cliente.post(
                f"/admin/vinculos/{vinculo_original_id}/reativar",
                headers=headers,
            )

            return resposta.status_code, resposta.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_a = executor.submit(
            reativar,
            "admin-concorrente-a@exemplo.test",
        )
        futuro_b = executor.submit(
            reativar,
            "admin-concorrente-b@exemplo.test",
        )

        resultados = [
            futuro_a.result(timeout=15),
            futuro_b.result(timeout=15),
        ]

    # Uma reativação deve ser confirmada.
    # A outra deve ser rejeitada por duplicidade.
    codigos = sorted(
        codigo for codigo, _ in resultados
    )

    assert codigos == [201, 409]

    # Verificar a integridade dos vínculos persistidos.
    with Session(db) as sessao:
        vinculos = sessao.scalars(
            select(ResponsavelAluno)
            .where(
                ResponsavelAluno.responsavel_id == responsavel_id,
                ResponsavelAluno.aluno_id == ctx["aluno_id"],
            )
            .order_by(ResponsavelAluno.id)
        ).all()

        assert len(vinculos) == 2

        original, novo = vinculos

        assert original.id == vinculo_original_id
        assert original.revogado_em is not None

        assert novo.id != original.id
        assert novo.revogado_em is None


def test_criacao_e_reativacao_concorrentes_nao_duplicam_vinculo(
    client_db,
    contexto_vinculo,
    criar_responsavel,
    criar_usuario,
    db,
    relogio,
):
    # ARRANGE — vínculo original
    ctx = contexto_vinculo
    responsavel_id = criar_responsavel()
    aluno_id = ctx["aluno_id"]

    criado = criar_vinculo(
        client_db,
        ctx["headers"],
        responsavel_id,
        aluno_id,
    )
    assert criado.status_code == 201

    vinculo_original_id = criado.json()["id"]

    # Revogar o vínculo original.
    relogio.avancar(seconds=1)

    revogado = client_db.post(
        f"/admin/vinculos/{vinculo_original_id}/revogar",
        headers=ctx["headers"],
    )

    assert revogado.status_code == 200
    assert revogado.json()["ativo"] is False

    # Garantir que o novo vínculo terá início posterior.
    relogio.avancar(seconds=1)

    # Criar duas contas administrativas distintas.
    criar_usuario(
        email="admin-criacao@exemplo.test",
        perfil=Perfil.ADMIN,
    )

    criar_usuario(
        email="admin-reativacao@exemplo.test",
        perfil=Perfil.ADMIN,
    )

    from app.main import app

    barreira = Barrier(2, timeout=10)

    def executar_operacao(email, operacao):
        # Cada thread possui seu próprio cliente HTTP
        # e seu próprio cookie de sessão.
        with TestClient(app) as cliente:
            autenticacao = login(
                cliente,
                email=email,
            )

            assert autenticacao.status_code == 200

            headers = {
                "X-CSRF-Token": autenticacao.json()[
                    "csrf_token"
                ]
            }

            # Sincronizar o início das requisições.
            barreira.wait()

            if operacao == "criar":
                resposta = cliente.post(
                    "/admin/vinculos",
                    json={
                        "responsavel_id": responsavel_id,
                        "aluno_id": aluno_id,
                    },
                    headers=headers,
                )

            else:
                resposta = cliente.post(
                    f"/admin/vinculos/{vinculo_original_id}/reativar",
                    headers=headers,
                )

            return resposta.status_code, resposta.json()

    # ACT — criação e reativação concorrentes
    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_criacao = executor.submit(
            executar_operacao,
            "admin-criacao@exemplo.test",
            "criar",
        )

        futuro_reativacao = executor.submit(
            executar_operacao,
            "admin-reativacao@exemplo.test",
            "reativar",
        )

        resultados = [
            futuro_criacao.result(timeout=15),
            futuro_reativacao.result(timeout=15),
        ]

    # ASSERT — uma operação vence, outra é rejeitada.
    codigos = sorted(
        codigo for codigo, _ in resultados
    )

    assert codigos == [201, 409]

    # ASSERT — histórico preservado e somente
    # um vínculo ativo para o par.
    with Session(db) as sessao:
        vinculos = sessao.scalars(
            select(ResponsavelAluno)
            .where(
                ResponsavelAluno.responsavel_id
                == responsavel_id,
                ResponsavelAluno.aluno_id == aluno_id,
            )
            .order_by(ResponsavelAluno.id)
        ).all()

        assert len(vinculos) == 2

        original = next(
            v for v in vinculos
            if v.id == vinculo_original_id
        )

        assert original.revogado_em is not None

        ativos = [
            v for v in vinculos
            if v.revogado_em is None
        ]

        assert len(ativos) == 1
        assert ativos[0].id != vinculo_original_id
        assert (
            ativos[0].vigente_desde
            > original.revogado_em
        )
