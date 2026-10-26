from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from app.domain.erros import DataNaoPermitida


def exigir_instante_com_fuso(instante: datetime) -> datetime:
    if instante.tzinfo is None or instante.utcoffset() is None:
        raise ValueError("O instante deve ter fuso horario (datetime aware).")
    return instante


class Relogio(Protocol):
    def agora(self) -> datetime: ...


class RelogioSistema:
    def agora(self) -> datetime:
        return datetime.now(UTC)


class RelogioFixo:
    """Relogio controlavel para testes."""

    def __init__(self, instante: datetime) -> None:
        self._instante = exigir_instante_com_fuso(instante)

    def agora(self) -> datetime:
        return self._instante


def data_escolar(agora: datetime, fuso: str) -> date:
    """Data oficial da escola no fuso configurado (nunca o fuso da maquina)."""
    return exigir_instante_com_fuso(agora).astimezone(ZoneInfo(fuso)).date()


def validar_data_alvo(solicitada: date, *, hoje: date) -> date:
    if solicitada != hoje:
        raise DataNaoPermitida(f"Operacao permitida somente para hoje ({hoje}).")
    return solicitada