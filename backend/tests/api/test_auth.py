"""E4a - autenticacao: login, cookie de sessao, CSRF, logout e protecao contra abuso."""
import re

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.seguranca import hash_token
from app.models import Sessao, Usuario
from tests.api.conftest import SENHA, login

pytestmark = pytest.mark.integration

EMAIL = "pessoa@exemplo.test"
CREDENCIAIS_INVALIDAS = {"detail": "Credenciais invalidas."}


# ---------------------------------------------------------------- login e cookie


def test_login_valido_retorna_usuario_e_token_csrf(client_db, criar_usuario):
    criar_usuario()
    r = login(client_db)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["usuario"]["email"] == EMAIL
    assert corpo["usuario"]["perfil"] == "RESPONSAVEL"
    assert len(corpo["csrf_token"]) == 64
    assert "senha" not in str(corpo).lower()
    assert "hash" not in str(corpo).lower()


def test_cookie_de_sessao_tem_atributos_de_seguranca(client_db, criar_usuario):
    criar_usuario()
    cabecalho = login(client_db).headers["set-cookie"]
    assert cabecalho.startswith("sessao=")
    assert "HttpOnly" in cabecalho
    assert "SameSite=lax" in cabecalho
    assert "Path=/" in cabecalho
    assert "Max-Age=28800" in cabecalho  # 8 horas


def test_cookie_e_secure_quando_configurado(client_db, criar_usuario, settings_teste):
    criar_usuario()
    settings_teste.cookie_secure = True
    assert "Secure" in login(client_db).headers["set-cookie"]


def test_banco_guarda_somente_o_hash_do_token(client_db, criar_usuario, db):
    criar_usuario()
    login(client_db)
    token = client_db.cookies.get("sessao")
    with Session(db) as s:
        sessao = s.scalars(select(Sessao)).one()
    assert sessao.token_hash != token
    assert sessao.token_hash == hash_token(token)


def test_cada_login_gera_um_token_novo(client_db, criar_usuario):
    criar_usuario()
    login(client_db)
    primeiro = client_db.cookies.get("sessao")
    login(client_db)
    assert client_db.cookies.get("sessao") != primeiro


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": EMAIL},
        {"senha": SENHA},
        {"email": EMAIL, "senha": ""},
        {"email": "", "senha": SENHA},
        {"email": EMAIL, "senha": "x" * 5000},
    ],
)
def test_login_com_dados_invalidos_e_rejeitado_na_validacao(client_db, payload):
    assert client_db.post("/auth/login", json=payload).status_code == 422


# ------------------------------------------------- falhas de login nao revelam nada


def test_falhas_de_login_tem_resposta_identica(client_db, criar_usuario):
    criar_usuario()
    criar_usuario(email="inativo@exemplo.test", ativo=False)
    senha_errada = login(client_db, EMAIL, "senha-errada")
    inexistente = login(client_db, "ninguem@exemplo.test", SENHA)
    inativo = login(client_db, "inativo@exemplo.test", SENHA)
    for r in (senha_errada, inexistente, inativo):
        assert r.status_code == 401
        assert r.json() == CREDENCIAIS_INVALIDAS
        assert "set-cookie" not in r.headers


def test_login_normaliza_o_email(client_db, criar_usuario):
    criar_usuario()
    assert login(client_db, "  PESSOA@Exemplo.TEST ").status_code == 200


# ------------------------------------------------------ eventos de seguranca


def test_login_falho_e_registrado_sem_dados_sensiveis(client_db, criar_usuario, eventos):
    criar_usuario()
    login(client_db, EMAIL, "minha-senha-errada-xyz")
    registrados = eventos("LOGIN_FALHA")
    assert len(registrados) == 1
    texto = str(registrados[0].detalhes) + str(registrados[0].entidade)
    assert EMAIL not in texto
    assert "minha-senha-errada-xyz" not in texto
    assert re.fullmatch(r"[0-9a-f]{64}", registrados[0].detalhes["chave"])


def test_login_bem_sucedido_e_registrado(client_db, criar_usuario, eventos):
    uid = criar_usuario()
    login(client_db)
    registrados = eventos("LOGIN_SUCESSO")
    assert len(registrados) == 1
    assert registrados[0].usuario_id == uid
    assert registrados[0].perfil.value == "RESPONSAVEL"


# --------------------------------------------------------- /auth/me e sessao


def test_me_sem_cookie_retorna_401(client_db):
    assert client_db.get("/auth/me").status_code == 401


def test_me_com_sessao_valida_retorna_usuario_e_csrf(client_db, criar_usuario):
    criar_usuario()
    csrf = login(client_db).json()["csrf_token"]
    r = client_db.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["usuario"]["email"] == EMAIL
    assert r.json()["csrf_token"] == csrf


@pytest.mark.parametrize("cookie", ["", "invalido", "a" * 43, "../../etc/passwd"])
def test_cookie_forjado_ou_invalido_retorna_401(client_db, cookie):
    client_db.cookies.set("sessao", cookie)
    assert client_db.get("/auth/me").status_code == 401


def test_sessao_expira_por_inatividade(client_db, criar_usuario, relogio):
    criar_usuario()
    login(client_db)
    relogio.avancar(minutes=29)
    assert client_db.get("/auth/me").status_code == 200
    relogio.avancar(minutes=30)  # 30 min sem acesso: limite exclusivo
    assert client_db.get("/auth/me").status_code == 401


def test_atividade_renova_a_inatividade_mas_nao_o_limite_absoluto(
    client_db, criar_usuario, relogio
):
    criar_usuario()
    login(client_db)
    decorrido = 0
    while decorrido + 29 < 480:  # acessos a cada 29 min mantem a sessao viva
        relogio.avancar(minutes=29)
        decorrido += 29
        assert client_db.get("/auth/me").status_code == 200
    relogio.avancar(minutes=29)  # passa das 8 horas, mesmo com acesso recente
    assert client_db.get("/auth/me").status_code == 401


def test_sessao_revogada_no_banco_retorna_401(client_db, criar_usuario, db, relogio):
    criar_usuario()
    login(client_db)
    with Session(db) as s:
        sessao = s.scalars(select(Sessao)).one()
        sessao.revogada_em = relogio.agora()
        s.commit()
    assert client_db.get("/auth/me").status_code == 401


def test_usuario_desativado_perde_o_acesso_na_proxima_requisicao(client_db, criar_usuario, db):
    uid = criar_usuario()
    login(client_db)
    assert client_db.get("/auth/me").status_code == 200
    with Session(db) as s:
        s.get(Usuario, uid).ativo = False
        s.commit()
    assert client_db.get("/auth/me").status_code == 401


# ------------------------------------------------------------- CSRF e logout


def test_logout_sem_token_csrf_e_rejeitado_e_a_sessao_continua(
    client_db, criar_usuario, eventos
):
    criar_usuario()
    login(client_db)
    r = client_db.post("/auth/logout")
    assert r.status_code == 403
    assert client_db.get("/auth/me").status_code == 200
    assert len(eventos("CSRF_INVALIDO")) == 1


def test_logout_com_token_csrf_errado_e_rejeitado(client_db, criar_usuario):
    criar_usuario()
    login(client_db)
    r = client_db.post("/auth/logout", headers={"X-CSRF-Token": "0" * 64})
    assert r.status_code == 403


def test_token_csrf_de_outra_sessao_e_rejeitado(client_db, criar_usuario):
    criar_usuario()
    csrf_antigo = login(client_db).json()["csrf_token"]
    login(client_db)  # nova sessao: novo token de sessao, novo CSRF
    r = client_db.post("/auth/logout", headers={"X-CSRF-Token": csrf_antigo})
    assert r.status_code == 403


def test_logout_valido_revoga_a_sessao_e_limpa_o_cookie(
    client_db, criar_usuario, db, eventos
):
    criar_usuario()
    csrf = login(client_db).json()["csrf_token"]
    token = client_db.cookies.get("sessao")
    r = client_db.post("/auth/logout", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 204
    assert "sessao=" in r.headers["set-cookie"]
    assert "Max-Age=0" in r.headers["set-cookie"]
    with Session(db) as s:
        sessao = s.scalars(select(Sessao)).one()
        assert sessao.revogada_em is not None
    client_db.cookies.set("sessao", token)  # reapresenta o token antigo
    assert client_db.get("/auth/me").status_code == 401
    assert len(eventos("LOGOUT")) == 1


def test_logout_sem_sessao_retorna_401(client_db):
    assert client_db.post("/auth/logout").status_code == 401


# ----------------------------------------------- protecao contra tentativas abusivas


def falhar(client, n, email=EMAIL):
    for _ in range(n):
        assert login(client, email, "senha-errada").status_code == 401


def test_apos_5_falhas_o_login_e_bloqueado_mesmo_com_a_senha_correta(
    client_db, criar_usuario, eventos
):
    criar_usuario()
    falhar(client_db, 5)
    r = login(client_db)
    assert r.status_code == 429
    assert 1 <= int(r.headers["Retry-After"]) <= 15 * 60
    assert len(eventos("LOGIN_BLOQUEADO")) == 1


def test_a_quarta_falha_ainda_nao_bloqueia(client_db, criar_usuario):
    criar_usuario()
    falhar(client_db, 4)
    assert login(client_db).status_code == 200


def test_bloqueio_expira_apos_a_janela(client_db, criar_usuario, relogio):
    criar_usuario()
    falhar(client_db, 5)
    assert login(client_db).status_code == 429
    relogio.avancar(minutes=14, seconds=59)
    assert login(client_db).status_code == 429
    relogio.avancar(seconds=2)
    assert login(client_db).status_code == 200


def test_tentativas_bloqueadas_nao_prorrogam_o_bloqueio(client_db, criar_usuario, relogio):
    criar_usuario()
    falhar(client_db, 5)
    for _ in range(3):
        assert login(client_db).status_code == 429
    relogio.avancar(minutes=15, seconds=1)
    assert login(client_db).status_code == 200


def test_bloqueio_de_um_email_nao_afeta_outro(client_db, criar_usuario):
    criar_usuario()
    criar_usuario(email="outra@exemplo.test")
    falhar(client_db, 5)
    assert login(client_db).status_code == 429
    assert login(client_db, "outra@exemplo.test").status_code == 200


def test_login_bem_sucedido_zera_a_contagem_de_falhas(client_db, criar_usuario):
    criar_usuario()
    falhar(client_db, 4)
    assert login(client_db).status_code == 200
    falhar(client_db, 4)
    assert login(client_db).status_code == 200


def test_bloqueio_vale_tambem_para_email_inexistente(client_db):
    falhar(client_db, 5, email="fantasma@exemplo.test")
    assert login(client_db, "fantasma@exemplo.test").status_code == 429


def test_muitas_falhas_do_mesmo_ip_bloqueiam_qualquer_email(client_db, criar_usuario):
    criar_usuario()
    for i in range(20):  # emails diferentes: nenhum atinge o limite por email
        assert login(client_db, f"alvo{i}@exemplo.test", "x").status_code == 401
    assert login(client_db).status_code == 429


def test_usuario_inexistente_e_inativo_gastam_tempo_de_verificacao(
    client_db, criar_usuario, monkeypatch
):
    chamadas = []
    monkeypatch.setattr(
        "app.services.autenticacao.gastar_tempo_de_verificacao", lambda s: chamadas.append(s)
    )
    criar_usuario(email="inativo@exemplo.test", ativo=False)
    login(client_db, "fantasma@exemplo.test")
    login(client_db, "inativo@exemplo.test")
    assert len(chamadas) == 2