"""E2 - data oficial da escola: calculada no backend, no fuso configurado (Aditivo, secao 1)."""
import time
from datetime import UTC, date, datetime

import pytest

from app.domain.erros import DataNaoPermitida
from app.domain.relogio import RelogioFixo, data_escolar, validar_data_alvo

SP = "America/Sao_Paulo"


def utc(*args):
    return datetime(*args, tzinfo=UTC)


def test_data_escolar_meio_do_dia():
    assert data_escolar(utc(2026, 10, 20, 15, 0), SP) == date(2026, 10, 20)


def test_virada_de_dia_no_fuso_da_escola_ainda_no_dia_anterior():
    # 02:59 UTC = 23:59 em Brasilia (UTC-3): ainda dia 20
    assert data_escolar(utc(2026, 10, 21, 2, 59), SP) == date(2026, 10, 20)


def test_virada_de_dia_no_fuso_da_escola_novo_dia():
    # 03:00 UTC = 00:00 em Brasilia: ja e dia 21
    assert data_escolar(utc(2026, 10, 21, 3, 0), SP) == date(2026, 10, 21)


def test_instante_sem_fuso_e_rejeitado():
    with pytest.raises(ValueError):
        data_escolar(datetime(2026, 10, 20, 12, 0), SP)


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="time.tzset nao existe no Windows")
def test_nao_depende_do_fuso_da_maquina(monkeypatch):
    instante = utc(2026, 10, 21, 2, 30)  # 23:30 em Brasilia
    esperado = data_escolar(instante, SP)
    monkeypatch.setenv("TZ", "Pacific/Auckland")
    time.tzset()
    try:
        assert data_escolar(instante, SP) == esperado == date(2026, 10, 20)
    finally:
        monkeypatch.delenv("TZ", raising=False)
        time.tzset()


def test_relogio_fixo_devolve_o_instante_configurado():
    instante = utc(2026, 10, 20, 12, 0)
    assert RelogioFixo(instante).agora() == instante


def test_relogio_fixo_exige_instante_com_fuso():
    with pytest.raises(ValueError):
        RelogioFixo(datetime(2026, 10, 20, 12, 0))


HOJE = date(2026, 10, 20)


def test_data_alvo_hoje_e_aceita():
    assert validar_data_alvo(HOJE, hoje=HOJE) == HOJE


@pytest.mark.parametrize("solicitada", [date(2026, 10, 19), date(2026, 10, 21)])
def test_data_alvo_diferente_de_hoje_e_rejeitada(solicitada):
    with pytest.raises(DataNaoPermitida):
        validar_data_alvo(solicitada, hoje=HOJE)