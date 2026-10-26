
"""Consulta autorizada da agenda efetiva de um aluno."""

from datetime import date, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import (
    Aluno,
    AnoLetivo,
    Matricula,
    ResponsavelAluno,
    Turma,
)

from app.services.agenda_efetiva import AgendaEfetiva
from app.services.consulta_agenda_efetiva import (
    consultar_agenda_efetiva,
)


class AgendaAlunoNaoDisponivel(ValueError):
    """Aluno não autorizado ou sem matrícula válida."""


def consultar_agenda_do_aluno(
    db: Session,
    *,
    responsavel_id: int,
    aluno_id: int,
    data: date,
    agora: datetime,
) -> tuple[int, AgendaEfetiva]:
    """
    Identifica a turma autorizada e consulta sua agenda.

    Não recebe turma_id do frontend.
    """

    vinculo = db.scalar(
        select(ResponsavelAluno.id)
        .where(
            ResponsavelAluno.responsavel_id == responsavel_id,
            ResponsavelAluno.aluno_id == aluno_id,
            ResponsavelAluno.vigente_desde <= agora,
            or_(
                ResponsavelAluno.revogado_em.is_(None),
                ResponsavelAluno.revogado_em > agora,
            ),
        )
        .limit(1)
    )

    if vinculo is None:
        raise AgendaAlunoNaoDisponivel(
            "Agenda do aluno não disponível."
        )

    matricula = db.scalar(
        select(Matricula)
        .join(
            Turma,
            Matricula.turma_id == Turma.id,
        )
        .join(
            AnoLetivo,
            Matricula.ano_letivo_id == AnoLetivo.id,
        )
        .join(
            Aluno,
            Matricula.aluno_id == Aluno.id,
        )
        .where(
            Matricula.aluno_id == aluno_id,
            Matricula.data_inicio <= data,
            or_(
                Matricula.data_fim.is_(None),
                Matricula.data_fim >= data,
            ),
            Matricula.ano_letivo_id == Turma.ano_letivo_id,
            Aluno.ativo.is_(True),
            Turma.ativo.is_(True),
            AnoLetivo.ativo.is_(True),
        )
        .order_by(
            Matricula.data_inicio.desc(),
            Matricula.id.desc(),
        )
        .limit(1)
    )

    if matricula is None:
        raise AgendaAlunoNaoDisponivel(
            "Agenda do aluno não disponível."
        )

    agenda = consultar_agenda_efetiva(
        db,
        turma_id=matricula.turma_id,
        data=data,
    )

    return matricula.turma_id, agenda
