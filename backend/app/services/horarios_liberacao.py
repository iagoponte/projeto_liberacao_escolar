
"""Regras de seleção de horário para liberação escolar."""

from datetime import date, time

from app.services.agenda_efetiva import AgendaEfetiva


class HorarioLiberacaoInvalido(ValueError):
    """Horário incompatível com a agenda efetiva."""


def horarios_disponiveis_liberacao(
    agenda: AgendaEfetiva,
) -> tuple[time, ...]:
    """Retorna o início das atividades elegíveis.

    Intervalos não oferecem um horário de liberação próprio.
    Eventos substitutivos e aulas regulares são elegíveis.
    """
    return tuple(
        sorted({
            atividade.hora_inicio
            for atividade in agenda.atividades
            if atividade.tipo in ("AULA", "EVENTO")
        })
    )


def validar_horario_liberacao(
    *,
    data_solicitada: date,
    data_escolar_atual: date,
    horario_solicitado: time,
    agenda: AgendaEfetiva,
) -> None:
    """Valida uma liberação para a data escolar atual."""

    if data_solicitada != data_escolar_atual:
        raise HorarioLiberacaoInvalido(
            "A liberação só pode ser registrada "
            "para a data atual da escola."
        )

    if agenda.data != data_solicitada:
        raise HorarioLiberacaoInvalido(
            "A agenda não corresponde à data solicitada."
        )

    horarios_permitidos = horarios_disponiveis_liberacao(
        agenda
    )

    if not horarios_permitidos:
        raise HorarioLiberacaoInvalido(
            "Não há atividades disponíveis "
            "para liberação nesta data."
        )

    if horario_solicitado not in horarios_permitidos:
        raise HorarioLiberacaoInvalido(
            "O horário selecionado não corresponde "
            "ao início de uma atividade da agenda."
        )
