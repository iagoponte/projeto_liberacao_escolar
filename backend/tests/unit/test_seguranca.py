"""E4 - primitivas de seguranca: hash de senha, token de sessao, CSRF."""
import re

import pytest

from app.core.seguranca import (
    chave_de_tentativa,
    csrf_valido,
    gastar_tempo_de_verificacao,
    hash_senha,
    hash_token,
    novo_token_sessao,
    token_csrf,
    verificar_senha,
)

SEGREDO = "s" * 48
OUTRO_SEGREDO = "t" * 48


@pytest.fixture(scope="module")
def hash_exemplo():
    return hash_senha("senha-ficticia-123")


def test_hash_usa_argon2id_e_nao_guarda_a_senha(hash_exemplo):
    assert hash_exemplo.startswith("$argon2id$")
    assert "senha-ficticia-123" not in hash_exemplo


def test_hash_tem_sal_proprio():
    assert hash_senha("mesma-senha") != hash_senha("mesma-senha")


def test_verifica_senha_correta_e_rejeita_incorreta(hash_exemplo):
    assert verificar_senha("senha-ficticia-123", hash_exemplo) is True
    assert verificar_senha("senha-errada", hash_exemplo) is False


@pytest.mark.parametrize("invalido", ["", "nao-e-um-hash", "$argon2id$quebrado"])
def test_hash_invalido_nunca_levanta_excecao(invalido):
    assert verificar_senha("qualquer", invalido) is False


def test_verificacao_de_tempo_constante_nao_levanta_excecao():
    gastar_tempo_de_verificacao("qualquer")


def test_token_de_sessao_e_imprevisivel_e_longo():
    tokens = {novo_token_sessao() for _ in range(50)}
    assert len(tokens) == 50
    assert all(len(t) >= 43 for t in tokens)  # 32 bytes em base64 url-safe


def test_hash_do_token_e_sha256_hex_deterministico():
    h = hash_token("abc")
    assert re.fullmatch(r"[0-9a-f]{64}", h)
    assert h == hash_token("abc")
    assert h != hash_token("abd")
    assert "abc" not in h


def test_csrf_e_deterministico_por_sessao_e_segredo():
    t = token_csrf(SEGREDO, "sessao-1")
    assert t == token_csrf(SEGREDO, "sessao-1")
    assert t != token_csrf(SEGREDO, "sessao-2")
    assert t != token_csrf(OUTRO_SEGREDO, "sessao-1")


def test_csrf_valido_aceita_somente_o_token_da_propria_sessao():
    t = token_csrf(SEGREDO, "sessao-1")
    assert csrf_valido(SEGREDO, "sessao-1", t) is True
    assert csrf_valido(SEGREDO, "sessao-2", t) is False
    assert csrf_valido(SEGREDO, "sessao-1", "adulterado") is False
    assert csrf_valido(SEGREDO, "sessao-1", "") is False
    assert csrf_valido(SEGREDO, "sessao-1", None) is False


def test_csrf_nao_e_igual_ao_token_da_sessao():
    assert token_csrf(SEGREDO, "sessao-1") != "sessao-1"
    assert token_csrf(SEGREDO, "sessao-1") != hash_token("sessao-1")


def test_chave_de_tentativa_normaliza_e_nao_expoe_o_email():
    a = chave_de_tentativa("  Pessoa@Exemplo.TEST ")
    assert a == chave_de_tentativa("pessoa@exemplo.test")
    assert re.fullmatch(r"[0-9a-f]{64}", a)
    assert "pessoa" not in a