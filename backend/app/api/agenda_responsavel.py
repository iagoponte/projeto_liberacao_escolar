
"""Consulta da agenda escolar pelos responsáveis."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import (
    Autenticado,
    autenticado,
    exigir_responsavel,
    get_db,
    get_relogio,
)
from app.domain.relogio import Relogio
from app.models import (
    AnoLetivo,
    EventoAgenda,
    Matricula,
    Responsavel,
    ResponsavelAluno,
    Turma,
)
from app.schemas.eventos import EventoResposta
from app.schemas.agenda_efetiva import AgendaAlunoResposta
from app.services.agenda_efetiva_responsavel import (
    AgendaAlunoNaoDisponivel,
    consultar_agenda_do_aluno,
)
from app.services.consulta_agenda_efetiva import (
    ErroConsultaAgenda,
)


router = APIRouter(
    prefix="/responsavel/agenda",
    tags=["Responsavel - Agenda"],
    dependencies=[Depends(exigir_responsavel)],
)


def obter_responsavel_autenticado(
    db: Session,
    auth: Autenticado,
) -> Responsavel:
    """
    Recupera o responsável ativo associado
    ao usuário autenticado.
    """

    responsavel = db.scalar(
        select(Responsavel).where(
            Responsavel.usuario_id == auth.usuario.id,
            Responsavel.ativo.is_(True),
        )
    )

    if responsavel is None:
        raise HTTPException(
            status_code=403,
            detail="Responsavel nao encontrado ou inativo.",
        )

    return responsavel


@router.get(
    "",
    response_model=list[EventoResposta],
)
def consultar_agenda_responsavel(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    db: Session = Depends(get_db),
    auth: Autenticado = Depends(autenticado),
    relogio: Relogio = Depends(get_relogio),
):
    """
    Consulta eventos escolares das turmas
    vinculadas aos alunos do responsável.
    """

    # 1. Validar intervalo solicitado.
    if (
        data_inicio is not None
        and data_fim is not None
        and data_fim < data_inicio
    ):
        raise HTTPException(
            status_code=422,
            detail="A data final nao pode ser anterior a inicial.",
        )

    # 2. Identificar o responsável autenticado.
    responsavel = obter_responsavel_autenticado(
        db,
        auth,
    )

    agora = relogio.agora()

    # 3. Consultar eventos das turmas autorizadas.
    consulta = (
        select(EventoAgenda)
        .join(
            Turma,
            EventoAgenda.turma_id == Turma.id,
        )
        .join(
            AnoLetivo,
            Turma.ano_letivo_id == AnoLetivo.id,
        )
        .join(
            Matricula,
            Matricula.turma_id == Turma.id,
        )
        .join(
            ResponsavelAluno,
            ResponsavelAluno.aluno_id == Matricula.aluno_id,
        )
        .where(
            EventoAgenda.ativo.is_(True),
            Turma.ativo.is_(True),
            AnoLetivo.ativo.is_(True),
            ResponsavelAluno.responsavel_id
            == responsavel.id,
            ResponsavelAluno.vigente_desde <= agora,
            or_(
                ResponsavelAluno.revogado_em.is_(None),
                ResponsavelAluno.revogado_em > agora,
            ),
            Matricula.data_inicio
            <= EventoAgenda.data_fim,
            or_(
                Matricula.data_fim.is_(None),
                Matricula.data_fim
                >= EventoAgenda.data_inicio,
            ),
            Matricula.ano_letivo_id
            == AnoLetivo.id,
        )
        .distinct()
    )

    # 4. Aplicar filtros opcionais de data.
    if data_inicio is not None:
        consulta = consulta.where(
            EventoAgenda.data_fim >= data_inicio
        )

    if data_fim is not None:
        consulta = consulta.where(
            EventoAgenda.data_inicio <= data_fim
        )

    # 5. Ordenar os eventos.
    consulta = consulta.order_by(
        EventoAgenda.data_inicio,
        EventoAgenda.id,
    )

    return db.scalars(consulta).all()


@router.get(
    "/alunos/{aluno_id}/agenda-efetiva",
    response_model=AgendaAlunoResposta,
)
def consultar_agenda_efetiva_responsavel(
    aluno_id: int,
    data: date,
    db: Session = Depends(get_db),
    auth: Autenticado = Depends(autenticado),
    relogio: Relogio = Depends(get_relogio),
):
    """
    Consulta a programação efetiva do aluno.

    Inclui:
    - Aulas da grade semanal;
    - Intervalos;
    - Eventos substitutivos;
    - Eventos informativos.

    O serviço valida o vínculo do responsável
    com o aluno e a matrícula correspondente.
    """

    # 1. Identificar o responsável autenticado.
    responsavel = obter_responsavel_autenticado(
        db,
        auth,
    )

    # 2. Obter o instante atual.
    agora = relogio.agora()

    # 3. Consultar a agenda efetiva do aluno.
    try:
        turma_id, agenda = consultar_agenda_do_aluno(
            db,
            responsavel_id=responsavel.id,
            aluno_id=aluno_id,
            data=data,
            agora=agora,
        )

    except AgendaAlunoNaoDisponivel as exc:
        raise HTTPException(
            status_code=404,
            detail="Agenda do aluno nao disponivel.",
        ) from exc

    except ErroConsultaAgenda as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    # 4. Construir a resposta.
    return AgendaAlunoResposta(
        aluno_id=aluno_id,
        turma_id=turma_id,
        data=agenda.data,
        atividades=[
            {
                "hora_inicio": item.hora_inicio,
                "hora_fim": item.hora_fim,
                "descricao": item.descricao,
                "tipo": item.tipo,
                "origem": item.origem,
                "evento_id": item.evento_id,
            }
            for item in agenda.atividades
        ],
        informativos=[
            {
                "id": evento.id,
                "titulo": evento.titulo,
                "data_inicio": evento.data_inicio,
                "data_fim": evento.data_fim,
                "hora_inicio": evento.hora_inicio,
                "hora_fim": evento.hora_fim,
                "modo_aplicacao": evento.modo_aplicacao,
            }
            for evento in agenda.informativos
        ],
    )
