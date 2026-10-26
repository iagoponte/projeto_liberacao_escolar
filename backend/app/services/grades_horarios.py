
"""Persistência e versionamento das grades horárias."""

from datetime import date, timedelta, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AnoLetivo,
    AulaRecorrente,
    GradeHorario,
    Turma,
)
from app.services.importacao_grade import GradeImportada


class ErroGrade(ValueError):
    pass


def salvar_grade(
    db: Session,
    turma_id: int,
    vigente_desde: date,
    grade_importada: GradeImportada,
    hora_termino: time,
) -> GradeHorario:
    try:
        # Serializa importacoes concorrentes da mesma turma.
        turma = db.scalar(
            select(Turma)
            .where(Turma.id == turma_id)
            .with_for_update()
        )

        if turma is None:
            raise ErroGrade("Turma nao encontrada.")

        if not turma.ativo:
            raise ErroGrade("Turma inativa.")

        ano_letivo = db.get(
            AnoLetivo,
            turma.ano_letivo_id,
        )

        if ano_letivo is None or not ano_letivo.ativo:
            raise ErroGrade("Ano letivo inexistente ou inativo.")

        if vigente_desde.year != ano_letivo.ano:
            raise ErroGrade(
                "A vigencia deve iniciar no ano letivo da turma."
            )
        
        if hora_termino <= grade_importada.horarios[-1]:
            raise ErroGrade(
                "O término da grade deve ser posterior "
                "ao último horário informado no CSV."
            )

        anterior = db.scalar(
            select(GradeHorario)
            .where(GradeHorario.turma_id == turma_id)
            .order_by(
                GradeHorario.vigente_desde.desc(),
                GradeHorario.id.desc(),
            )
            .limit(1)
        )

        if anterior is not None:
            if anterior.vigente_ate is None:
                if vigente_desde <= anterior.vigente_desde:
                    raise ErroGrade(
                        "A nova grade deve iniciar depois da "
                        "grade vigente."
                    )

                anterior.vigente_ate = (
                    vigente_desde - timedelta(days=1)
                )

                # Libera a restricao de uma grade aberta
                # por turma antes de inserir a proxima.
                db.flush()

            elif vigente_desde <= anterior.vigente_ate:
                raise ErroGrade(
                    "O periodo informado conflita com "
                    "uma grade existente."
                )

        nova = GradeHorario(
            turma_id=turma_id,
            vigente_desde=vigente_desde,
            vigente_ate=None,
            horarios=[
                horario.strftime("%H:%M")
                for horario in grade_importada.horarios
            ],
            hora_termino=hora_termino,
        )

        db.add(nova)
        db.flush()

        for aula in grade_importada.aulas:
            db.add(
                AulaRecorrente(
                    grade_id=nova.id,
                    dia_semana=aula.dia_semana,
                    hora_inicio=aula.hora_inicio,
                    descricao=aula.descricao,
                    tipo=aula.tipo,
                )
            )

        db.flush()
        db.commit()
        db.refresh(nova)

        return nova

    except Exception:
        db.rollback()
        raise
