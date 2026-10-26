"""E2 - orquestracao das regras: perfil, vinculo, limite do turno, data e transicao."""
from datetime import UTC, date, datetime, timedelta

import pytest

from app.domain.avaliacao import PedidoOperacao, avaliar_operacao
from app.domain.erros import (
    DataNaoPermitida,
    ForaDoHorarioLimite,
    MotivoObrigatorio,
    TransicaoInvalida,
    VinculoInvalido,
)
from app.domain.estados import Acao, Estado, Mudanca, Perfil, Redundante, TipoAcao
from app.domain.turno import Turno
from app.domain.vinculo import Vinculo

SP = "America/Sao_Paulo"


def brasilia(hora, minuto=0, dia=20):
    return datetime(2026, 10, dia, hora, minuto, tzinfo=UTC) + timedelta(hours=3)


VINCULO_OK = Vinculo(
    responsavel_id=1, aluno_id=10, vigente_desde=datetime(2026, 1, 1, tzinfo=UTC)
)
VINCULO_REVOGADO = Vinculo(
    responsavel_id=1,
    aluno_id=10,
    vigente_desde=datetime(2026, 1, 1, tzinfo=UTC),
    revogado_em=datetime(2026, 10, 10, tzinfo=UTC),
)


def pedido(**kw):
    base = dict(
        perfil=Perfil.RESPONSAVEL,
        acao=Acao.LIBERAR,
        estado_atual=None,
        agora=brasilia(10),
        fuso=SP,
        turno=Turno.MANHA,
        vinculo=VINCULO_OK,
        motivo=None,
        data_solicitada=None,
    )
    base.update(kw)
    return PedidoOperacao(**base)


def test_responsavel_libera_com_vinculo_vigente_dentro_do_limite():
    r = avaliar_operacao(pedido())
    assert r.data_alvo == date(2026, 10, 20)
    assert r.decisao == Mudanca(None, Estado.LIBERADO, TipoAcao.LIBERACAO)


def test_data_alvo_vem_do_relogio_da_escola_e_nao_do_pedido():
    # 23:30 em Brasilia (02:30 UTC do dia 21): a data da escola ainda e 20.
    # Admin, pois o responsavel ja estaria fora do limite do turno.
    r = avaliar_operacao(
        pedido(
            perfil=Perfil.ADMIN,
            motivo="Ajuste",
            vinculo=None,
            agora=datetime(2026, 10, 21, 2, 30, tzinfo=UTC),
        )
    )
    assert r.data_alvo == date(2026, 10, 20)


@pytest.mark.parametrize("data", [date(2026, 10, 19), date(2026, 10, 21)])
def test_data_solicitada_diferente_de_hoje_e_rejeitada(data):
    with pytest.raises(DataNaoPermitida):
        avaliar_operacao(pedido(data_solicitada=data))


def test_data_solicitada_igual_a_hoje_e_aceita():
    assert avaliar_operacao(pedido(data_solicitada=date(2026, 10, 20))).data_alvo == date(
        2026, 10, 20
    )


def test_responsavel_sem_vinculo_e_rejeitado():
    with pytest.raises(VinculoInvalido):
        avaliar_operacao(pedido(vinculo=None))


def test_responsavel_com_vinculo_revogado_e_rejeitado():
    with pytest.raises(VinculoInvalido):
        avaliar_operacao(pedido(vinculo=VINCULO_REVOGADO))


@pytest.mark.parametrize("acao", [Acao.LIBERAR, Acao.CANCELAR])
def test_responsavel_apos_o_limite_nao_pode_nenhuma_acao(acao):
    with pytest.raises(ForaDoHorarioLimite):
        avaliar_operacao(pedido(acao=acao, estado_atual=Estado.LIBERADO, agora=brasilia(13, 0)))


def test_responsavel_as_12_59_ainda_pode():
    assert isinstance(avaliar_operacao(pedido(agora=brasilia(12, 59))).decisao, Mudanca)


def test_turno_noite_limite_19h():
    ok = avaliar_operacao(pedido(turno=Turno.NOITE, agora=brasilia(18, 59)))
    assert isinstance(ok.decisao, Mudanca)
    with pytest.raises(ForaDoHorarioLimite):
        avaliar_operacao(pedido(turno=Turno.NOITE, agora=brasilia(19, 0)))


def test_responsavel_redundante_nao_gera_mudanca():
    r = avaliar_operacao(pedido(estado_atual=Estado.LIBERADO))
    assert r.decisao == Redundante(estado=Estado.LIBERADO)


def test_responsavel_transicao_invalida_e_rejeitada():
    with pytest.raises(TransicaoInvalida):
        avaliar_operacao(pedido(acao=Acao.CANCELAR, estado_atual=None))


def test_admin_ignora_vinculo_e_limite_mas_exige_motivo():
    r = avaliar_operacao(
        pedido(
            perfil=Perfil.ADMIN,
            vinculo=None,
            agora=brasilia(20, 0),
            estado_atual=Estado.LIBERADO,
            acao=Acao.CANCELAR,
            motivo="Erro do responsavel",
        )
    )
    assert r.decisao == Mudanca(Estado.LIBERADO, Estado.CANCELADO, TipoAcao.CORRECAO_ADMIN)


def test_admin_sem_motivo_e_rejeitado_mesmo_apos_o_limite():
    with pytest.raises(MotivoObrigatorio):
        avaliar_operacao(pedido(perfil=Perfil.ADMIN, vinculo=None, agora=brasilia(20, 0)))


def test_admin_tambem_so_opera_na_data_atual():
    with pytest.raises(DataNaoPermitida):
        avaliar_operacao(
            pedido(
                perfil=Perfil.ADMIN,
                motivo="x",
                vinculo=None,
                data_solicitada=date(2026, 10, 19),
            )
        )