"""E2 - vinculo responsavel-aluno: vigente vs. revogado (Aditivo, secao 5)."""
from datetime import UTC, datetime

from app.domain.vinculo import Vinculo


def t(dia, hora=12):
    return datetime(2026, 10, dia, hora, 0, tzinfo=UTC)


def test_vinculo_sem_revogacao_e_vigente_apos_o_inicio():
    v = Vinculo(responsavel_id=1, aluno_id=10, vigente_desde=t(1))
    assert v.vigente_em(t(20)) is True


def test_vinculo_ainda_nao_iniciado_nao_e_vigente():
    v = Vinculo(responsavel_id=1, aluno_id=10, vigente_desde=t(25))
    assert v.vigente_em(t(20)) is False


def test_vinculo_revogado_antes_do_instante_nao_e_vigente():
    v = Vinculo(responsavel_id=1, aluno_id=10, vigente_desde=t(1), revogado_em=t(15))
    assert v.vigente_em(t(20)) is False


def test_vinculo_vigente_ate_o_instante_exato_da_revogacao_exclusive():
    v = Vinculo(responsavel_id=1, aluno_id=10, vigente_desde=t(1), revogado_em=t(15))
    assert v.vigente_em(t(14, 23)) is True
    assert v.vigente_em(t(15)) is False