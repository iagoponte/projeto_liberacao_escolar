"""Testes de autorizacao e acesso aos alunos — E4b (RED)."""

import pytest

from app.domain.estados import Perfil
from tests.api.conftest import login

pytestmark = pytest.mark.integration


def test_admin_pode_listar_alunos(client_db, criar_usuario):
    criar_usuario(perfil=Perfil.ADMIN)
    assert login(client_db).status_code == 200

    resposta = client_db.get("/admin/alunos")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_responsavel_nao_pode_acessar_lista_administrativa(
    client_db, criar_usuario
):
    criar_usuario(perfil=Perfil.RESPONSAVEL)
    assert login(client_db).status_code == 200

    resposta = client_db.get("/admin/alunos")

    assert resposta.status_code == 403


def test_responsavel_pode_listar_seus_alunos(client_db, criar_usuario):
    criar_usuario(perfil=Perfil.RESPONSAVEL)
    assert login(client_db).status_code == 200

    resposta = client_db.get("/responsavel/alunos")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_admin_nao_pode_acessar_lista_de_responsavel(
    client_db, criar_usuario
):
    criar_usuario(perfil=Perfil.ADMIN)
    assert login(client_db).status_code == 200

    resposta = client_db.get("/responsavel/alunos")

    assert resposta.status_code == 403


def test_usuario_nao_autenticado_nao_pode_listar_alunos(client_db):
    resposta_admin = client_db.get("/admin/alunos")
    resposta_responsavel = client_db.get("/responsavel/alunos")

    assert resposta_admin.status_code == 401
    assert resposta_responsavel.status_code == 401


from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import Aluno, Responsavel, ResponsavelAluno


def criar_cenario_aluno(
    db,
    usuario_id,
    relogio,
    *,
    aluno_ativo=True,
    responsavel_ativo=True,
    inicio=None,
    revogacao=None,
):
    """Cria responsavel, aluno e vinculo em um banco de teste."""

    with Session(db) as session:
        responsavel = Responsavel(
            usuario_id=usuario_id,
            nome_completo="Responsavel de Teste",
            ativo=responsavel_ativo,
        )
        aluno = Aluno(
            nome_completo="Aluno de Teste",
            ativo=aluno_ativo,
        )

        session.add_all([responsavel, aluno])
        session.flush()

        vinculo = ResponsavelAluno(
            responsavel_id=responsavel.id,
            aluno_id=aluno.id,
            vigente_desde=inicio or relogio.agora() - timedelta(days=30),
            revogado_em=revogacao,
        )

        session.add(vinculo)
        session.commit()

        return aluno.id


def test_responsavel_lista_apenas_alunos_vinculados(
    client_db, criar_usuario, db, relogio
):
    usuario_id = criar_usuario()

    aluno_autorizado = criar_cenario_aluno(
        db, usuario_id, relogio
    )

    with Session(db) as session:
        outro_aluno = Aluno(nome_completo="Aluno sem vinculo")
        session.add(outro_aluno)
        session.commit()
        outro_aluno_id = outro_aluno.id

    assert login(client_db).status_code == 200

    resposta = client_db.get("/responsavel/alunos")

    assert resposta.status_code == 200

    ids = {aluno["id"] for aluno in resposta.json()}

    assert aluno_autorizado in ids
    assert outro_aluno_id not in ids


def test_responsavel_nao_consulta_aluno_sem_vinculo(
    client_db, criar_usuario, db
):
    criar_usuario()

    with Session(db) as session:
        aluno = Aluno(nome_completo="Aluno de outro responsavel")
        session.add(aluno)
        session.commit()
        aluno_id = aluno.id

    assert login(client_db).status_code == 200

    resposta = client_db.get(f"/responsavel/alunos/{aluno_id}")

    assert resposta.status_code == 404


def test_aluno_inativo_nao_aparece_na_lista(
    client_db, criar_usuario, db, relogio
):
    usuario_id = criar_usuario()

    aluno_id = criar_cenario_aluno(
        db,
        usuario_id,
        relogio,
        aluno_ativo=False,
    )

    assert login(client_db).status_code == 200

    resposta = client_db.get("/responsavel/alunos")

    assert resposta.status_code == 200
    assert aluno_id not in {
        aluno["id"] for aluno in resposta.json()
    }


def test_vinculo_revogado_nao_concede_acesso(
    client_db, criar_usuario, db, relogio
):
    usuario_id = criar_usuario()

    aluno_id = criar_cenario_aluno(
        db,
        usuario_id,
        relogio,
        revogacao=relogio.agora() - timedelta(days=1),
    )

    assert login(client_db).status_code == 200

    resposta = client_db.get(
        f"/responsavel/alunos/{aluno_id}"
    )

    assert resposta.status_code == 404


def test_vinculo_futuro_nao_concede_acesso(
    client_db, criar_usuario, db, relogio
):
    usuario_id = criar_usuario()

    aluno_id = criar_cenario_aluno(
        db,
        usuario_id,
        relogio,
        inicio=relogio.agora() + timedelta(days=1),
    )

    assert login(client_db).status_code == 200

    resposta = client_db.get(
        f"/responsavel/alunos/{aluno_id}"
    )

    assert resposta.status_code == 404


def test_responsavel_inativo_nao_acessa_alunos(
    client_db, criar_usuario, db, relogio
):
    usuario_id = criar_usuario()

    aluno_id = criar_cenario_aluno(
        db,
        usuario_id,
        relogio,
        responsavel_ativo=False,
    )

    assert login(client_db).status_code == 200

    resposta = client_db.get(
        f"/responsavel/alunos/{aluno_id}"
    )

    assert resposta.status_code == 404


def test_responsavel_consulta_aluno_autorizado(
    client_db, criar_usuario, db, relogio
):
    usuario_id = criar_usuario()

    aluno_id = criar_cenario_aluno(
        db, usuario_id, relogio
    )

    assert login(client_db).status_code == 200

    resposta = client_db.get(
        f"/responsavel/alunos/{aluno_id}"
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["id"] == aluno_id
    assert dados["nome_completo"] == "Aluno de Teste"


def test_listagem_admin_nao_expoe_senha_hash(
    client_db, criar_usuario, db
):
    criar_usuario(perfil=Perfil.ADMIN)

    with Session(db) as session:
        session.add(Aluno(nome_completo="Aluno Administrativo"))
        session.commit()

    assert login(client_db).status_code == 200

    resposta = client_db.get("/admin/alunos")

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1
    assert "senha_hash" not in resposta.json()[0]



from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import Aluno, ResponsavelAluno


def test_dois_responsaveis_nao_acessam_alunos_um_do_outro(
    client_db, criar_usuario, db, relogio
):
    usuario_a = criar_usuario(email="responsavel-a@exemplo.test")
    usuario_b = criar_usuario(email="responsavel-b@exemplo.test")

    aluno_a = criar_cenario_aluno(db, usuario_a, relogio)
    aluno_b = criar_cenario_aluno(db, usuario_b, relogio)

    assert login(
        client_db, email="responsavel-a@exemplo.test"
    ).status_code == 200

    resposta = client_db.get("/responsavel/alunos")

    assert resposta.status_code == 200
    assert {item["id"] for item in resposta.json()} == {aluno_a}

    assert client_db.get(
        f"/responsavel/alunos/{aluno_b}"
    ).status_code == 404

    assert login(
        client_db, email="responsavel-b@exemplo.test"
    ).status_code == 200

    resposta = client_db.get("/responsavel/alunos")

    assert resposta.status_code == 200
    assert {item["id"] for item in resposta.json()} == {aluno_b}

    assert client_db.get(
        f"/responsavel/alunos/{aluno_a}"
    ).status_code == 404


def test_vinculo_valido_no_instante_exato_do_inicio(
    client_db, criar_usuario, db, relogio
):
    usuario_id = criar_usuario()
    aluno_id = criar_cenario_aluno(
        db,
        usuario_id,
        relogio,
        inicio=relogio.agora(),
    )

    assert login(client_db).status_code == 200

    resposta = client_db.get(f"/responsavel/alunos/{aluno_id}")

    assert resposta.status_code == 200


def test_vinculo_revogado_no_instante_exato_nao_concede_acesso(
    client_db, criar_usuario, db, relogio
):
    usuario_id = criar_usuario()

    aluno_id = criar_cenario_aluno(
        db,
        usuario_id,
        relogio,
        inicio=relogio.agora() - timedelta(days=10),
        revogacao=relogio.agora(),
    )

    assert login(client_db).status_code == 200

    resposta = client_db.get(f"/responsavel/alunos/{aluno_id}")

    assert resposta.status_code == 404


def test_aluno_inativo_nao_pode_ser_consultado_individualmente(
    client_db, criar_usuario, db, relogio
):
    usuario_id = criar_usuario()

    aluno_id = criar_cenario_aluno(
        db,
        usuario_id,
        relogio,
        aluno_ativo=False,
    )

    assert login(client_db).status_code == 200

    resposta = client_db.get(f"/responsavel/alunos/{aluno_id}")

    assert resposta.status_code == 404


def test_consulta_individual_exige_autenticacao(client_db):
    resposta = client_db.get("/responsavel/alunos/1")

    assert resposta.status_code == 401


def test_responsavel_nao_ve_aluno_com_vinculo_revogado_na_listagem(
    client_db, criar_usuario, db, relogio
):
    usuario_id = criar_usuario()

    aluno_id = criar_cenario_aluno(
        db,
        usuario_id,
        relogio,
        revogacao=relogio.agora() - timedelta(days=1),
    )

    assert login(client_db).status_code == 200

    resposta = client_db.get("/responsavel/alunos")

    assert resposta.status_code == 200
    assert aluno_id not in {
        item["id"] for item in resposta.json()
    }


def test_vinculo_historico_nao_duplica_aluno(
    client_db, criar_usuario, db, relogio
):
    usuario_id = criar_usuario()

    aluno_id = criar_cenario_aluno(
        db,
        usuario_id,
        relogio,
        inicio=relogio.agora() - timedelta(days=10),
    )

    with Session(db) as session:
        vinculo_atual = session.query(ResponsavelAluno).filter_by(
            aluno_id=aluno_id
        ).one()

        # Encerra o primeiro vinculo no passado.
        vinculo_atual.revogado_em = (
            relogio.agora() - timedelta(days=5)
        )
        session.flush()

        # Cria novo vinculo vigente para o mesmo responsavel e aluno.
        novo_vinculo = ResponsavelAluno(
            responsavel_id=vinculo_atual.responsavel_id,
            aluno_id=aluno_id,
            vigente_desde=relogio.agora() - timedelta(days=2),
            revogado_em=None,
        )

        session.add(novo_vinculo)
        session.commit()

    assert login(client_db).status_code == 200

    resposta = client_db.get("/responsavel/alunos")

    assert resposta.status_code == 200

    ids = [item["id"] for item in resposta.json()]

    assert ids.count(aluno_id) == 1
