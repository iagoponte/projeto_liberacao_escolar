"""E4 - regras puras de sessao: revogacao, expiracao absoluta e por inatividade."""
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.sessao import (
    MotivoSessaoInvalida,
    avaliar_sessao,
    calcular_expiracao,
    deve_renovar_ultimo_acesso,
)

T0 = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
IDLE = timedelta(minutes=30)
EXPIRA = T0 + timedelta(hours=8)


def avaliar(agora, ultimo_acesso=T0, expira_em=EXPIRA, revogada_em=None):
    return avaliar_sessao(
        agora=agora,
        expira_em=expira_em,
        ultimo_acesso_em=ultimo_acesso,
        revogada_em=revogada_em,
        inatividade_maxima=IDLE,
    )


def test_sessao_recem_criada_e_valida():
    assert avaliar(T0) is None


def test_sessao_ativa_dentro_dos_limites_e_valida():
    assert avaliar(T0 + timedelta(minutes=29, seconds=59)) is None


def test_inatividade_no_limite_exato_expira():
    assert avaliar(T0 + IDLE) is MotivoSessaoInvalida.EXPIRADA_INATIVIDADE


def test_acesso_recente_mantem_a_sessao_viva_ate_o_limite_absoluto():
    ultimo = EXPIRA - timedelta(minutes=5)
    assert avaliar(EXPIRA - timedelta(seconds=1), ultimo_acesso=ultimo) is None


def test_expiracao_absoluta_no_limite_exato_expira_mesmo_com_acesso_recente():
    ultimo = EXPIRA - timedelta(seconds=10)
    assert avaliar(EXPIRA, ultimo_acesso=ultimo) is MotivoSessaoInvalida.EXPIRADA_ABSOLUTA


def test_sessao_revogada_e_invalida_mesmo_dentro_dos_prazos():
    assert avaliar(T0, revogada_em=T0) is MotivoSessaoInvalida.REVOGADA


def test_revogacao_tem_precedencia_sobre_os_prazos():
    agora = EXPIRA + timedelta(hours=1)
    assert avaliar(agora, revogada_em=T0) is MotivoSessaoInvalida.REVOGADA


@pytest.mark.parametrize("campo", ["agora", "expira_em", "ultimo_acesso_em"])
def test_instantes_sem_fuso_sao_rejeitados(campo):
    kw = dict(
        agora=T0,
        expira_em=EXPIRA,
        ultimo_acesso_em=T0,
        revogada_em=None,
        inatividade_maxima=IDLE,
    )
    kw[campo] = kw[campo].replace(tzinfo=None)
    with pytest.raises(ValueError):
        avaliar_sessao(**kw)


def test_calcular_expiracao_soma_os_minutos():
    assert calcular_expiracao(T0, 480) == T0 + timedelta(hours=8)


@pytest.mark.parametrize(
    ("segundos", "esperado"), [(0, False), (59, False), (60, True), (600, True)]
)
def test_renovacao_do_ultimo_acesso_so_apos_um_minuto(segundos, esperado):
    agora = T0 + timedelta(seconds=segundos)
    assert deve_renovar_ultimo_acesso(agora, T0) is esperado