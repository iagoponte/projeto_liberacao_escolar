from datetime import datetime, time
from enum import StrEnum
from zoneinfo import ZoneInfo

from app.domain.relogio import exigir_instante_com_fuso


class Turno(StrEnum):
    # Nomes definidos na E3: MANHA (limite 13:00) e NOITE (limite 19:00).
    MANHA = "MANHA"
    NOITE = "NOITE"


LIMITES: dict[Turno, time] = {
    Turno.MANHA: time(13, 0),
    Turno.NOITE: time(19, 0),
}


def dentro_do_limite(agora: datetime, fuso: str, turno: Turno) -> bool:
    """True enquanto o horario local for ESTRITAMENTE anterior ao limite do turno."""
    local = exigir_instante_com_fuso(agora).astimezone(ZoneInfo(fuso))
    return local.time() < LIMITES[turno]