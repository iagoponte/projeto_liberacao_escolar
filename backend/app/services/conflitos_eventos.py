
"""Detecção de conflitos entre eventos substitutivos."""

from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EventoAgenda

INFORMATIVO = "INFORMATIVO"
PARCIAL = "SUBSTITUICAO_PARCIAL"
INTEGRAL = "SUBSTITUICAO_INTEGRAL"


def encontrar_conflito_evento(
    db: Session,
    *,
    turma_id: int,
    data_inicio: date,
    data_fim: date,
    modo_aplicacao: str,
    hora_inicio: time | None,
    hora_fim: time | None,
    ignorar_evento_id: int | None = None,
) -> EventoAgenda | None:
    """Retorna um evento conflitante, se existir.

    Intervalos horários são semiabertos: [início, fim).
    Assim, eventos das 14:00 às 15:00 e das
    15:00 às 16:00 não entram em conflito.
    """

    if modo_aplicacao == INFORMATIVO:
        return None

    consulta = select(EventoAgenda).where(
        EventoAgenda.ativo.is_(True),
        EventoAgenda.turma_id == turma_id,
        EventoAgenda.modo_aplicacao != INFORMATIVO,
        EventoAgenda.data_inicio <= data_fim,
        EventoAgenda.data_fim >= data_inicio,
    )

    if ignorar_evento_id is not None:
        consulta = consulta.where(
            EventoAgenda.id != ignorar_evento_id
        )

    candidatos = db.scalars(consulta).all()

    for evento in candidatos:
        # Um evento integral ocupa a programação
        # de todas as datas abrangidas.
        if (
            modo_aplicacao == INTEGRAL
            or evento.modo_aplicacao == INTEGRAL
        ):
            return evento

        # Eventos parciais precisam de horários.
        # Os schemas e o banco já devem garantir isso.
        if (
            hora_inicio is None
            or hora_fim is None
            or evento.hora_inicio is None
            or evento.hora_fim is None
        ):
            raise ValueError(
                "Evento parcial sem intervalo válido."
            )

        if (
            hora_inicio < evento.hora_fim
            and hora_fim > evento.hora_inicio
        ):
            return evento

    return None
