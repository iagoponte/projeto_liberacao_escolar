"""E2 - maquina de estados explicita: todas as transicoes permitidas e rejeitadas."""
import pytest

from app.domain.erros import MotivoObrigatorio, TransicaoInvalida
from app.domain.estados import (
    Acao,
    Estado,
    Mudanca,
    Perfil,
    Redundante,
    TipoAcao,
    decidir_transicao,
)

R, A = Perfil.RESPONSAVEL, Perfil.ADMIN
LIB, CAN = Estado.LIBERADO, Estado.CANCELADO


@pytest.mark.parametrize(
    ("atual", "acao", "novo", "tipo"),
    [
        (None, Acao.LIBERAR, LIB, TipoAcao.LIBERACAO),
        (LIB, Acao.CANCELAR, CAN, TipoAcao.CANCELAMENTO),
        (CAN, Acao.LIBERAR, LIB, TipoAcao.LIBERACAO),
    ],
)
def test_transicoes_permitidas_do_responsavel(atual, acao, novo, tipo):
    r = decidir_transicao(atual, acao, R)
    assert r == Mudanca(estado_anterior=atual, novo_estado=novo, tipo_acao=tipo)


@pytest.mark.parametrize(("atual", "acao"), [(LIB, Acao.LIBERAR), (CAN, Acao.CANCELAR)])
@pytest.mark.parametrize("perfil", [R, A])
def test_operacao_redundante_nao_gera_mudanca(atual, acao, perfil):
    motivo = "ajuste" if perfil is A else None
    assert decidir_transicao(atual, acao, perfil, motivo=motivo) == Redundante(estado=atual)


def test_responsavel_nao_pode_cancelar_sem_registro():
    with pytest.raises(TransicaoInvalida):
        decidir_transicao(None, Acao.CANCELAR, R)


@pytest.mark.parametrize(
    ("atual", "acao", "novo"),
    [
        (None, Acao.LIBERAR, LIB),
        (None, Acao.CANCELAR, CAN),
        (LIB, Acao.CANCELAR, CAN),
        (CAN, Acao.LIBERAR, LIB),
    ],
)
def test_admin_corrige_com_motivo_e_gera_correcao_admin(atual, acao, novo):
    r = decidir_transicao(atual, acao, A, motivo="Pedido da coordenacao")
    assert r == Mudanca(estado_anterior=atual, novo_estado=novo, tipo_acao=TipoAcao.CORRECAO_ADMIN)


@pytest.mark.parametrize("motivo", [None, "", "   "])
def test_admin_sem_motivo_e_rejeitado(motivo):
    with pytest.raises(MotivoObrigatorio):
        decidir_transicao(None, Acao.LIBERAR, A, motivo=motivo)


def test_motivo_nao_e_exigido_do_responsavel():
    assert isinstance(decidir_transicao(None, Acao.LIBERAR, R), Mudanca)


def test_estado_e_acao_nao_aceitam_valores_arbitrarios():
    with pytest.raises(ValueError):
        Estado("NAO_LIBERADO")
    with pytest.raises(ValueError):
        Acao("DESFAZER_CANCELAMENTO")