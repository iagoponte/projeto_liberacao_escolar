
"""Consulta administrativa da programação escolar efetiva."""

from datetime import date, time
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import exigir_admin, get_db

from app.services.consulta_agenda_efetiva import (
    ErroConsultaAgenda,
    consultar_agenda_efetiva,
)


router = APIRouter(
    prefix="/admin/turmas",
    tags=["Admin - Agenda efetiva"],
    dependencies=[Depends(exigir_admin)],
)


class AtividadeEfetivaResposta(BaseModel):
    hora_inicio: time
    hora_fim: time
    descricao: str
    tipo: Literal["AULA", "INTERVALO", "EVENTO"]
    origem: Literal["GRADE", "EVENTO"]
    evento_id: int | None


class EventoInformativoResposta(BaseModel):
    id: int
    titulo: str
    data_inicio: date
    data_fim: date
    hora_inicio: time | None
    hora_fim: time | None
    modo_aplicacao: str


class AgendaEfetivaResposta(BaseModel):
    turma_id: int
    data: date
    atividades: list[AtividadeEfetivaResposta]
    informativos: list[EventoInformativoResposta]


@router.get(
    "/{turma_id}/agenda",
    response_model=AgendaEfetivaResposta,
)
def obter_agenda_turma(
    turma_id: int,
    data: date = Query(...),
    db: Session = Depends(get_db),
):
    try:
        agenda = consultar_agenda_efetiva(
            db,
            turma_id=turma_id,
            data=data,
        )
    except ErroConsultaAgenda as exc:
        mensagem = str(exc)

        codigo = (
            404
            if (
                mensagem == "Turma não encontrada."
                or mensagem.startswith(
                    "Não existe grade horária vigente"
                )
            )
            else 409
        )

        raise HTTPException(
            status_code=codigo,
            detail=mensagem,
        ) from exc

    return AgendaEfetivaResposta(
        turma_id=turma_id,
        data=agenda.data,
        atividades=[
            AtividadeEfetivaResposta(
                hora_inicio=atividade.hora_inicio,
                hora_fim=atividade.hora_fim,
                descricao=atividade.descricao,
                tipo=atividade.tipo,
                origem=atividade.origem,
                evento_id=atividade.evento_id,
            )
            for atividade in agenda.atividades
        ],
        informativos=[
            EventoInformativoResposta(
                id=evento.id,
                titulo=evento.titulo,
                data_inicio=evento.data_inicio,
                data_fim=evento.data_fim,
                hora_inicio=evento.hora_inicio,
                hora_fim=evento.hora_fim,
                modo_aplicacao=evento.modo_aplicacao,
            )
            for evento in agenda.informativos
        ],
    )
