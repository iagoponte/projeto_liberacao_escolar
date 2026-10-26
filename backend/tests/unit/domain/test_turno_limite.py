from datetime import UTC, datetime, timedelta

import pytest

from app.domain.turno import LIMITES, Turno, dentro_do_limite

SP = "America/Sao_Paulo"


def utc_de_brasilia(hora, minuto, segundo=0):
    # Brasilia = UTC-3 (sem horario de verao); 20/out/2026
    return datetime(2026, 10, 20, hora, minuto, segundo, tzinfo=UTC) + timedelta(hours=3)


def test_limites_configurados():
    assert LIMITES[Turno.MANHA].hour == 13
    assert LIMITES[Turno.NOITE].hour == 19


@pytest.mark.parametrize(
    ("turno", "h", "m", "s", "esperado"),
    [
        (Turno.MANHA, 7, 0, 0, True),
        (Turno.MANHA, 12, 59, 59, True),
        (Turno.MANHA, 13, 0, 0, False),
        (Turno.MANHA, 13, 0, 1, False),
        (Turno.NOITE, 18, 59, 59, True),
        (Turno.NOITE, 19, 0, 0, False),
        (Turno.NOITE, 22, 0, 0, False),
    ],
)
def test_fronteira_exclusiva_do_limite(turno, h, m, s, esperado):
    assert dentro_do_limite(utc_de_brasilia(h, m, s), SP, turno) is esperado


def test_instante_sem_fuso_e_rejeitado():
    with pytest.raises(ValueError):
        dentro_do_limite(datetime(2026, 10, 20, 10, 0), SP, Turno.NOITE)