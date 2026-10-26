
"""Consulta e consolidação da agenda escolar de uma turma."""

from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AulaRecorrente,
    EventoAgenda,
    GradeHorario,
    Turma,
)

from app.services.agenda_efetiva import (
    AgendaEfetiva,
    AulaDaGrade,
    EventoDoDia,
    construir_agenda_efetiva,
)


class ErroConsultaAgenda(ValueError):
    pass


def consultar_agenda_efetiva(
    db: Session,
    *,
    turma_id: int,
    data: date,
) -> AgendaEfetiva:
    """Retorna a programação efetiva da turma na data."""

    turma = db.get(Turma, turma_id)

    if turma is None:
        raise ErroConsultaAgenda(
            "Turma não encontrada."
        )

    # Seleciona a versão da grade válida naquela data.
    grade = db.scalar(
        select(GradeHorario)
        .where(
            GradeHorario.turma_id == turma_id,
            GradeHorario.vigente_desde <= data,
            (
                (GradeHorario.vigente_ate.is_(None))
                | (GradeHorario.vigente_ate >= data)
            ),
        )
        .order_by(
            GradeHorario.vigente_desde.desc(),
            GradeHorario.id.desc(),
        )
        .limit(1)
    )

    # A inexistência de grade não impede que a turma
    # possua eventos excepcionais naquela data.
    # Entretanto, para a consolidação da E9.3,
    # exigimos grade e encerramento conhecidos.
    if grade is None:
        raise ErroConsultaAgenda(
            "Não existe grade horária vigente "
            "para a turma na data informada."
        )

    if grade.hora_termino is None:
        raise ErroConsultaAgenda(
            "A grade vigente ainda não possui "
            "horário de término configurado."
        )

    try:
        horarios = [
            time.fromisoformat(horario)
            for horario in grade.horarios
        ]
    except (TypeError, ValueError) as exc:
        raise ErroConsultaAgenda(
            "A grade possui horários inválidos."
        ) from exc

    aulas_banco = db.scalars(
        select(AulaRecorrente)
        .where(
            AulaRecorrente.grade_id == grade.id,
            AulaRecorrente.dia_semana == data.weekday(),
        )
        .order_by(AulaRecorrente.hora_inicio)
    ).all()

    aulas = [
        AulaDaGrade(
            dia_semana=aula.dia_semana,
            hora_inicio=aula.hora_inicio,
            descricao=aula.descricao,
            tipo=aula.tipo,
        )
        for aula in aulas_banco
    ]

    eventos_banco = db.scalars(
        select(EventoAgenda)
        .where(
            EventoAgenda.turma_id == turma_id,
            EventoAgenda.ativo.is_(True),
            EventoAgenda.data_inicio <= data,
            EventoAgenda.data_fim >= data,
        )
        .order_by(
            EventoAgenda.data_inicio,
            EventoAgenda.id,
        )
    ).all()

    eventos = [
        EventoDoDia(
            id=evento.id,
            titulo=evento.titulo,
            data_inicio=evento.data_inicio,
            data_fim=evento.data_fim,
            modo_aplicacao=evento.modo_aplicacao,
            hora_inicio=evento.hora_inicio,
            hora_fim=evento.hora_fim,
        )
        for evento in eventos_banco
    ]

    try:
        return construir_agenda_efetiva(
            data=data,
            horarios=horarios,
            hora_termino=grade.hora_termino,
            aulas=aulas,
            eventos=eventos,
        )
    except ValueError as exc:
        raise ErroConsultaAgenda(str(exc)) from exc
